// Compare the capture area with its empty background; wait for it to clear
// before arming again so a stationary fruit is captured only once.
export class ArrivalDetector {
  constructor({ threshold = 0.12, calibrationFrames = 10, arrivalFrames = 2,
    clearFrames = 4, cooldownMs = 1000, pixelThreshold = 35 } = {}) {
    Object.assign(this, { threshold, calibrationFrames, arrivalFrames,
      clearFrames, cooldownMs, pixelThreshold });
    this.reset();
  }

  reset() {
    this.background = null;
    this.calibratedFrames = 0;
    this.presentFrames = 0;
    this.emptyFrames = 0;
    this.waitingForEmpty = false;
    this.lastCaptureAt = -Infinity;
  }

  update(pixels, now, busy = false) {
    if (!this.background || this.background.length !== pixels.length) {
      this.reset();
      this.background = Float32Array.from(pixels);
    }
    if (this.calibratedFrames < this.calibrationFrames) {
      const weight = 1 / (this.calibratedFrames + 1);
      for (let i = 0; i < pixels.length; i++) {
        this.background[i] += (pixels[i] - this.background[i]) * weight;
      }
      this.calibratedFrames += 1;
      return { trigger: false, phase: "calibrating", ratio: 0 };
    }

    let changed = 0;
    for (let i = 0; i < pixels.length; i += 4) {
      const difference = (Math.abs(pixels[i] - this.background[i])
        + Math.abs(pixels[i + 1] - this.background[i + 1])
        + Math.abs(pixels[i + 2] - this.background[i + 2])) / 3;
      if (difference >= this.pixelThreshold) changed += 1;
    }
    const ratio = changed / (pixels.length / 4);
    const empty = ratio < this.threshold * 0.45;
    if (this.waitingForEmpty) {
      this.emptyFrames = empty ? this.emptyFrames + 1 : 0;
      if (!busy && this.emptyFrames >= this.clearFrames && now - this.lastCaptureAt >= this.cooldownMs) {
        this.waitingForEmpty = false;
        this.presentFrames = 0;
        this.emptyFrames = 0;
      }
      return { trigger: false, phase: this.waitingForEmpty ? "waiting-clear" : "armed", ratio };
    }

    if (busy) {
      this.presentFrames = 0;
      // An object passing while a request is pending must clear before rearming.
      if (!empty) this.waitingForEmpty = true;
      return { trigger: false, phase: "busy", ratio };
    }

    this.presentFrames = ratio >= this.threshold ? this.presentFrames + 1 : 0;
    if (this.presentFrames >= this.arrivalFrames && now - this.lastCaptureAt >= this.cooldownMs) {
      this.waitingForEmpty = true;
      this.lastCaptureAt = now;
      this.emptyFrames = 0;
      return { trigger: true, phase: "captured", ratio };
    }
    return { trigger: false, phase: "armed", ratio };
  }
}

// The preview uses object-fit: cover. Map its central box to the same source
// pixels for detection and capture, including portrait cameras.
export function captureRegion(sourceWidth, sourceHeight, viewWidth, viewHeight) {
  const scale = Math.max(viewWidth / sourceWidth, viewHeight / sourceHeight);
  const visibleWidth = viewWidth / scale;
  const visibleHeight = viewHeight / scale;
  return {
    x: (sourceWidth - visibleWidth) / 2 + visibleWidth * 0.25,
    y: (sourceHeight - visibleHeight) / 2 + visibleHeight * 0.2,
    width: visibleWidth * 0.5,
    height: visibleHeight * 0.6,
  };
}
