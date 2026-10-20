"""Two independent readers; only validated, pinned HTTP destinations are opened.

HTTP is handled here rather than inside FFmpeg: this prevents automatic redirects
and DNS rebinding. OpenCV decodes/encodes the MJPEG frames. Viewers share immutable
JPEG bytes and never open another connection to the phone.
"""

import http.client
import ipaddress
import socket
import ssl
import time
from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import Event, Lock, RLock, Thread
from urllib.parse import urlsplit

from ..config import settings


class CameraError(ValueError):
    pass


LAN_NETWORKS = tuple(ipaddress.ip_network(item) for item in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7",
))
MAX_JPEG_BYTES = 10 * 1024 * 1024


def parse_url(url):
    if not url or not url.strip():
        raise CameraError("Chưa nhập URL camera.")
    if len(url) > 2048 or any(char.isspace() or ord(char) < 32 for char in url):
        raise CameraError("URL không được chứa khoảng trắng hoặc ký tự điều khiển.")
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.netloc.endswith(":"):
            raise ValueError()
        if parts.username is not None or parts.password is not None or parts.fragment:
            raise ValueError()
        if parts.port is not None and parts.port < 1:
            raise ValueError()
        parts.hostname.encode("ascii")
    except (ValueError, UnicodeError):
        raise CameraError("URL cần có dạng http(s)://IP:cong/video, không kèm tài khoản hoặc #fragment.") from None
    return parts


def resolve_camera(url):
    parts = parse_url(url)
    host = parts.hostname.lower()
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(
            host, port, type=socket.SOCK_STREAM,
        )))
    except OSError:
        raise CameraError("Không tìm được địa chỉ camera. Kiểm tra IP/tên máy và mạng Wi-Fi.") from None
    for value in addresses:
        address = ipaddress.ip_address(value)
        if address.is_unspecified or address.is_multicast or address.is_link_local or getattr(address, "ipv4_mapped", None):
            raise CameraError("Địa chỉ camera không được phép (link-local, multicast hoặc địa chỉ đặc biệt).")
        local = any(address.version == net.version and address in net for net in LAN_NETWORKS)
        if not local and host not in settings.camera_allowed_hosts:
            raise CameraError("Chỉ cho phép IP mạng nội bộ hoặc host trong CAMERA_ALLOWED_HOSTS.")
    if not addresses:
        raise CameraError("Không tìm được IP camera.")
    return parts, addresses[0], port


class PinnedConnection(http.client.HTTPConnection):
    def __init__(self, parts, address, port):
        super().__init__(parts.hostname, port, timeout=settings.camera_connect_timeout)
        self.address = address
        self.secure = parts.scheme == "https"
        self.transport_socket = None

    def connect(self):
        # Connect to the checked IP exactly once; never resolve the hostname again.
        self.sock = socket.create_connection((self.address, self.port), self.timeout)
        if self.secure:
            self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=self.host)
        self.sock.settimeout(settings.camera_read_timeout)
        self.transport_socket = self.sock


@dataclass(frozen=True)
class Frame:
    jpeg: bytes
    monotonic: float
    timestamp: str
    sequence: int
    simulation: bool = False
    rotation: int = 0


def rotate_image(image, rotation):
    import cv2
    rotations = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180,
                 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return cv2.rotate(image, rotations[rotation]) if rotation else image


def encode_jpeg(image):
    import cv2
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise CameraError("OpenCV không mã hóa được ảnh camera.")
    return encoded.tobytes()


class Camera:
    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.lock = RLock()
        self.operation = Lock()
        self.stop = Event()
        self.thread = None
        self.connection = None
        self.status = "Disconnected"
        self.error = ""
        self.simulation = False
        self.generation = 0
        self.started = 0.0
        self.sequence = 0
        self.frames = deque(maxlen=30)
        self.rotation = 0

    def set_rotation(self, rotation):
        if rotation not in (0, 90, 180, 270):
            raise CameraError("Góc xoay phải là 0, 90, 180 hoặc 270 độ.")
        with self.lock:
            if rotation == self.rotation:
                return
            # Update the latest cached frame immediately, retaining its real age.
            # Never leave frames from the previous orientation in paired captures.
            latest = self.frames[-1] if self.frames else None
            if latest:
                import cv2
                import numpy as np
                image = cv2.imdecode(np.frombuffer(latest.jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is None:
                    raise CameraError("Không xoay được khung hình hiện tại. Hãy kết nối lại camera.")
                jpeg = encode_jpeg(rotate_image(image, (rotation - self.rotation) % 360))
                self.sequence += 1
                self.frames.clear()
                self.frames.append(replace(latest, jpeg=jpeg, sequence=self.sequence, rotation=rotation))
            self.rotation = rotation

    def start(self, url, simulation=False):
        with self.operation:
            self._stop()
            with self.lock:
                self.stop = Event()
                self.status = "Connecting"
                self.error = ""
                self.simulation = simulation
                self.started = time.monotonic()
                self.generation += 1
                self.thread = Thread(target=self._read, args=(url,), daemon=True,
                                     name=f"camera-{self.camera_id}")
                self.thread.start()
        return self.snapshot()

    def _stop(self):
        with self.lock:
            self.stop.set()
            connection = self.connection
            thread = self.thread
            self.status = "Disconnected"
            self.error = ""
            self.frames.clear()
        # Interrupt an active read without releasing OpenCV buffers in another thread.
        if connection and connection.transport_socket:
            try:
                connection.transport_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if thread:
            thread.join(settings.camera_connect_timeout + settings.camera_read_timeout + 1)
            if thread.is_alive():
                raise CameraError("Tác vụ camera cũ đang đóng. Hãy thử kết nối lại sau vài giây.")
        with self.lock:
            self.thread = None

    def disconnect(self):
        with self.operation:
            self._stop()
        return self.snapshot()

    def snapshot(self):
        with self.lock:
            age = time.monotonic() - self.frames[-1].monotonic if self.frames else None
            if self.status == "Connected" and (age is None or age > settings.camera_frame_max_age):
                self.status = "Error"
                self.error = "Không nhận được khung hình mới. Kiểm tra điện thoại/Wi-Fi và nhấn Kết nối lại."
                self.stop.set()
            if self.status == "Connecting" and time.monotonic() - self.started > settings.camera_connect_timeout + settings.camera_read_timeout:
                self.status = "Error"
                self.error = "Hết thời gian kết nối. Kiểm tra camera server, IP, cổng và cùng mạng Wi-Fi."
                self.stop.set()
            return {"camera_id": self.camera_id, "status": self.status, "error": self.error,
                    "rotation": self.rotation,
                    "simulation": self.simulation, "generation": self.generation,
                    "frame_age_ms": round(age * 1000) if age is not None else None,
                    "timestamp": self.frames[-1].timestamp if self.frames else None}

    def _publish(self, frame):
        with self.lock:
            rotation = self.rotation
        jpeg = encode_jpeg(rotate_image(frame, rotation))
        with self.lock:
            if self.stop.is_set() or rotation != self.rotation:
                return
            self.sequence += 1
            self.frames.append(Frame(jpeg, time.monotonic(),
                                     datetime.now(timezone.utc).isoformat(), self.sequence, self.simulation, rotation))
            self.status = "Connected"

    def _read(self, url):
        connection = None
        response = None
        try:
            import cv2
            import numpy as np
            if self.simulation:
                while not self.stop.is_set():
                    frame = np.full((360, 640, 3), 245, dtype=np.uint8)
                    cv2.circle(frame, (320, 190), 85, (20, 140, 245), -1)
                    cv2.putText(frame, f"SIMULATION - CAMERA {self.camera_id}", (25, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, .7, (20, 20, 20), 2)
                    cv2.putText(frame, datetime.now(timezone.utc).isoformat()[:23], (25, 325),
                                cv2.FONT_HERSHEY_SIMPLEX, .6, (20, 20, 20), 1)
                    self._publish(frame)
                    self.stop.wait(.1)
                return
            parts, address, port = resolve_camera(url)
            if self.stop.is_set():
                return
            connection = PinnedConnection(parts, address, port)
            with self.lock:
                self.connection = connection
            path = parts.path or "/"
            if parts.query:
                path += "?" + parts.query
            connection.request("GET", path, headers={"Accept": "multipart/x-mixed-replace", "Connection": "close"})
            response = connection.getresponse()
            if 300 <= response.status < 400:
                raise CameraError("Camera trả chuyển hướng HTTP; hãy nhập trực tiếp URL MJPEG đích được phép.")
            if response.status in (401, 403):
                raise CameraError("Camera yêu cầu xác thực hoặc từ chối truy cập (401/403). Kiểm tra quyền trong ứng dụng camera.")
            if response.status != 200:
                raise CameraError(f"Camera trả HTTP {response.status}. Kiểm tra đường dẫn /video và cổng trong ứng dụng.")
            if "multipart/x-mixed-replace" not in response.getheader("Content-Type", "").lower():
                raise CameraError("URL không phải luồng HTTP/MJPEG. Hãy dùng URL video, không dùng trang quản trị hoặc ảnh tĩnh.")
            buffer = b""
            last_frame = time.monotonic()
            while not self.stop.is_set():
                chunk = response.read1(65536)
                if not chunk:
                    raise CameraError("Camera đã đóng luồng video. Kiểm tra ứng dụng và nhấn Kết nối lại.")
                buffer += chunk
                if len(buffer) > MAX_JPEG_BYTES:
                    raise CameraError("Khung hình MJPEG vượt giới hạn 10 MB hoặc luồng không hợp lệ.")
                while True:
                    start = buffer.find(b"\xff\xd8")
                    end = buffer.find(b"\xff\xd9", start + 2) if start >= 0 else -1
                    if end < 0:
                        break
                    jpeg, buffer = buffer[start:end + 2], buffer[end + 2:]
                    frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        continue
                    self._publish(frame)
                    last_frame = time.monotonic()
                if time.monotonic() - last_frame > settings.camera_frame_max_age:
                    raise CameraError("Luồng đang gửi dữ liệu nhưng không có khung hình JPEG mới hợp lệ.")
        except Exception as exc:
            if isinstance(exc, CameraError):
                detail = str(exc)
            elif isinstance(exc, ModuleNotFoundError):
                detail = "Thiếu OpenCV/numpy. Cài backend/requirements.txt rồi khởi động lại backend."
            elif isinstance(exc, (TimeoutError, socket.timeout)):
                detail = "Camera hết thời gian phản hồi. Kiểm tra camera server đã bật, đúng IP/cổng và cùng Wi-Fi."
            elif isinstance(exc, ConnectionRefusedError):
                detail = "Camera từ chối kết nối. Kiểm tra cổng và bật camera server trên điện thoại."
            elif isinstance(exc, ssl.SSLError):
                detail = "Chứng chỉ HTTPS camera không hợp lệ. Kiểm tra chứng chỉ hoặc dùng URL HTTP trong mạng nội bộ."
            else:
                detail = "Mất kết nối tới camera. Kiểm tra IP, Wi-Fi, tường lửa và ứng dụng phát video rồi kết nối lại."
            with self.lock:
                if not self.stop.is_set():
                    self.status, self.error = "Error", detail
        finally:
            if response:
                response.close()
            if connection:
                connection.close()
            with self.lock:
                self.connection = None


class CameraManager:
    def __init__(self):
        self.cameras = {camera_id: Camera(camera_id) for camera_id in (1, 2)}

    def get(self, camera_id):
        if camera_id not in self.cameras:
            raise CameraError("Camera không tồn tại; camera_id phải là 1 hoặc 2.")
        return self.cameras[camera_id]

    def capture(self, ids):
        cameras = [self.get(camera_id) for camera_id in sorted(ids)]
        # Keep a short frame history to choose the nearest pair. Copy references
        # under both locks; disk writes and AI run after releasing them.
        deadline = time.monotonic() + settings.camera_frame_max_age
        while True:
            for camera in cameras:
                camera.snapshot()
            for camera in cameras:
                camera.lock.acquire()
            try:
                now = time.monotonic()
                groups = []
                for camera in cameras:
                    frames = [frame for frame in camera.frames if now - frame.monotonic <= settings.camera_frame_max_age]
                    if camera.status != "Connected" or not frames:
                        raise CameraError(f"Camera {camera.camera_id} chưa kết nối hoặc không có khung hình mới. Không lưu ảnh cũ.")
                    groups.append(frames)
                if len(cameras) == 1:
                    return {ids[0]: groups[0][-1]}
                # Minimize skew among frames close to the newest shared time.
                target = min(group[-1].monotonic for group in groups)
                selected = [min(group, key=lambda frame: abs(frame.monotonic - target)) for group in groups]
                skew = abs(selected[0].monotonic - selected[1].monotonic)
                if skew <= settings.camera_pair_max_skew:
                    return dict(zip(sorted(ids), selected))
            finally:
                for camera in reversed(cameras):
                    camera.lock.release()
            if time.monotonic() >= deadline:
                raise CameraError("Không tìm được hai khung hình gần nhau trong giới hạn thời gian. Kiểm tra tốc độ hai camera rồi thử lại.")
            time.sleep(.03)

    def shutdown(self):
        for camera in self.cameras.values():
            try:
                camera.disconnect()
            except CameraError:
                pass
