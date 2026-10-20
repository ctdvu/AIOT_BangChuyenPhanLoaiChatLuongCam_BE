import test from "node:test";
import assert from "node:assert/strict";
import { ArrivalDetector, captureRegion } from "../src/arrivalDetector.js";

function frame(occupied = false) {
  return Uint8ClampedArray.from({ length: 100 * 4 }, (_, index) => {
    if (index % 4 === 3) return 255;
    return occupied && index < 40 * 4 ? 200 : 20;
  });
}

function readyDetector(options = {}) {
  const detector = new ArrivalDetector({ calibrationFrames: 2, ...options });
  assert.equal(detector.update(frame(), 0).phase, "calibrating");
  detector.update(frame(), 120);
  return detector;
}

test("empty background and a single noisy frame do not trigger", () => {
  const detector = readyDetector();
  for (let i = 2; i < 10; i++) assert.equal(detector.update(frame(), i * 120).trigger, false);
  assert.equal(detector.update(frame(true), 1200).trigger, false);
  assert.equal(detector.update(frame(), 1320).trigger, false);
});

test("one fruit generates one capture even if it stays in the capture area", () => {
  const detector = readyDetector();
  assert.equal(detector.update(frame(true), 240).trigger, false);
  assert.equal(detector.update(frame(true), 360).trigger, true);
  for (let now = 480; now < 6000; now += 120) {
    const result = detector.update(frame(true), now);
    assert.equal(result.trigger, false);
    assert.equal(result.phase, "waiting-clear");
  }
});

test("next fruit triggers only after area clears and cooldown expires", () => {
  const detector = readyDetector();
  detector.update(frame(true), 240);
  detector.update(frame(true), 360);
  for (let now = 480; now <= 1200; now += 120) detector.update(frame(), now);
  assert.equal(detector.update(frame(true), 1320).trigger, false);
  assert.equal(detector.update(frame(), 1440).phase, "waiting-clear");
  detector.update(frame(), 1560);
  detector.update(frame(), 1680);
  assert.equal(detector.update(frame(), 1800).phase, "armed");
  assert.equal(detector.update(frame(true), 1920).trigger, false);
  assert.equal(detector.update(frame(true), 2040).trigger, true);
});

test("pending inference blocks captures and ignores an overlapping fruit", () => {
  const detector = readyDetector();
  assert.equal(detector.update(frame(true), 240, true).trigger, false);
  assert.equal(detector.update(frame(true), 360, false).phase, "waiting-clear");
  for (let now = 480; now <= 840; now += 120) detector.update(frame(), now);
  detector.update(frame(true), 960);
  assert.equal(detector.update(frame(true), 1080).trigger, true);
});

test("reset calibrates a new background without immediately firing", () => {
  const detector = readyDetector();
  detector.update(frame(true), 240);
  detector.update(frame(true), 360);
  detector.reset();
  assert.equal(detector.update(frame(), 1000).phase, "calibrating");
});

test("capture region matches centered overlay for landscape and portrait", () => {
  assert.deepEqual(captureRegion(640, 480, 640, 360), {
    x: 160, y: 132, width: 320, height: 216,
  });
  const portrait = captureRegion(480, 640, 640, 360);
  assert.equal(portrait.width, 240);
  assert.equal(portrait.height, 162);
  assert.equal(portrait.x + portrait.width / 2, 240);
  assert.equal(portrait.y + portrait.height / 2, 320);
});
