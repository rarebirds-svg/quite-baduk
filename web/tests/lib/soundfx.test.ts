import { beforeEach, describe, expect, it, vi } from "vitest";

// Minimal Web Audio API stub. We only assert that the synth pipeline gets
// built — exact frequency / gain ramp values are sample-rate dependent
// and not interesting to lock down here. The visible side effects we
// care about are: createOscillator + start when enabled, none of that
// when disabled.
class FakeAudioParam {
  value = 0;
  setValueAtTime() { return this; }
  exponentialRampToValueAtTime() { return this; }
}
class FakeAudioNode {
  connect(next: FakeAudioNode) { return next; }
  disconnect() { return undefined; }
}
class FakeOscillator extends FakeAudioNode {
  type = "sine";
  frequency = new FakeAudioParam();
  static started: FakeOscillator[] = [];
  start() { FakeOscillator.started.push(this); }
  stop() { return undefined; }
}
class FakeGain extends FakeAudioNode {
  gain = new FakeAudioParam();
}
class FakeBufferSource extends FakeAudioNode {
  buffer: unknown = null;
  start() { return undefined; }
  stop() { return undefined; }
}
class FakeBiquad extends FakeAudioNode {
  type = "highpass";
  frequency = new FakeAudioParam();
  Q = new FakeAudioParam();
}
class FakeAudioContext {
  state = "running";
  currentTime = 0;
  sampleRate = 44_100;
  destination = new FakeAudioNode();
  createOscillator() { return new FakeOscillator(); }
  createGain() { return new FakeGain(); }
  createBufferSource() { return new FakeBufferSource(); }
  createBiquadFilter() { return new FakeBiquad(); }
  createBuffer(_ch: number, len: number) {
    const data = new Float32Array(len);
    return { sampleRate: this.sampleRate, getChannelData: () => data };
  }
  resume() { return Promise.resolve(); }
}

describe("soundfx", () => {
  beforeEach(() => {
    vi.stubGlobal("AudioContext", FakeAudioContext);
    FakeOscillator.started = [];
    localStorage.clear();
    vi.resetModules();
  });

  it("synthesizes a click when enabled", async () => {
    const { playStoneClick } = await import("@/lib/soundfx");
    playStoneClick();
    // The pitched body layer wires an oscillator and starts it. A single
    // call must produce at least one started oscillator — if it doesn't,
    // the synth pipeline got short-circuited.
    expect(FakeOscillator.started.length).toBeGreaterThan(0);
  });

  it("does not synthesize when disabled", async () => {
    const mod = await import("@/lib/soundfx");
    mod.setStoneSoundEnabled(false);
    mod.playStoneClick();
    expect(FakeOscillator.started.length).toBe(0);
  });

  it("persists the enabled flag in localStorage", async () => {
    const mod = await import("@/lib/soundfx");
    mod.setStoneSoundEnabled(false);
    expect(localStorage.getItem("sfx:stone")).toBe("0");
    mod.setStoneSoundEnabled(true);
    expect(localStorage.getItem("sfx:stone")).toBe("1");
  });

  it("is a no-op when AudioContext is unavailable", async () => {
    vi.stubGlobal("AudioContext", undefined);
    const { playStoneClick } = await import("@/lib/soundfx");
    expect(() => playStoneClick()).not.toThrow();
  });
});
