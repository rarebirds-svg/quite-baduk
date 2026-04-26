import { describe, it, expect, vi, beforeEach } from "vitest";

class FakeAudio {
  src: string;
  volume = 1;
  paused = true;
  static instances: FakeAudio[] = [];
  constructor(src: string) {
    this.src = src;
    FakeAudio.instances.push(this);
  }
  play() {
    this.paused = false;
    return Promise.resolve();
  }
  pause() {
    this.paused = true;
  }
  set currentTime(_v: number) {
    // no-op
  }
}

describe("soundfx", () => {
  beforeEach(() => {
    vi.stubGlobal("Audio", FakeAudio);
    FakeAudio.instances = [];
    localStorage.clear();
    vi.resetModules();
  });

  it("plays one sample from the pool when enabled", async () => {
    const { playStoneClick } = await import("@/lib/soundfx");
    playStoneClick();
    const playing = FakeAudio.instances.filter((a) => !a.paused);
    expect(playing.length).toBe(1);
    expect(playing[0].src).toMatch(/\/sounds\/stone-\d\.mp3$/);
  });

  it("does not play when disabled", async () => {
    const mod = await import("@/lib/soundfx");
    mod.setStoneSoundEnabled(false);
    mod.playStoneClick();
    const playing = FakeAudio.instances.filter((a) => !a.paused);
    expect(playing.length).toBe(0);
  });

  it("persists enabled flag in localStorage", async () => {
    const mod = await import("@/lib/soundfx");
    mod.setStoneSoundEnabled(false);
    expect(localStorage.getItem("sfx:stone")).toBe("0");
    mod.setStoneSoundEnabled(true);
    expect(localStorage.getItem("sfx:stone")).toBe("1");
  });
});
