/**
 * Stone-click SFX, synthesized with the Web Audio API.
 *
 * Replaces the earlier sample-based pool (mp3 of a real stone hitting a
 * board) which sounded "thudded" — too much wood resonance, not enough
 * top-end. Korean online sites (Tygem / Orobaduk / Hangame) all favour a
 * brighter, drier "tick" with a high-mid pitched body and a fast decay,
 * closer to a wooden block than a kaya board. We approximate that with:
 *
 *   1. A very short filtered-noise burst — the broadband transient that
 *      gives the click its "snap".
 *   2. A pitched sine ping centred ~2.5 kHz with tiny per-click jitter —
 *      the bright "tock" body. Damped quickly (~70 ms) so successive
 *      clicks don't smear into one another.
 *
 * Synthesis avoids shipping new sample files, lets us pitch-jitter for
 * a more natural feel, and stays well under 1 ms of audio thread work
 * per click. Falls back silently when AudioContext is unavailable.
 */

const STORAGE_KEY = "sfx:stone";

let enabled = true;
let ctx: AudioContext | null = null;

if (typeof window !== "undefined") {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "0") enabled = false;
}

type WindowWithWebkit = Window & { webkitAudioContext?: typeof AudioContext };

function getContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (ctx) return ctx;
  const w = window as WindowWithWebkit;
  const Ctor = window.AudioContext ?? w.webkitAudioContext;
  if (!Ctor) return null;
  try {
    ctx = new Ctor();
  } catch {
    return null;
  }
  return ctx;
}

export function setStoneSoundEnabled(on: boolean): void {
  enabled = on;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, on ? "1" : "0");
  }
}

export function isStoneSoundEnabled(): boolean {
  return enabled;
}

/**
 * Build a tiny stereo noise buffer once and reuse it for every click —
 * AudioBuffer is immutable and cheap to schedule against, so the actual
 * envelope shaping happens in the gain node per-click.
 */
let noiseBuffer: AudioBuffer | null = null;
function getNoiseBuffer(audioCtx: AudioContext): AudioBuffer {
  if (noiseBuffer && noiseBuffer.sampleRate === audioCtx.sampleRate) {
    return noiseBuffer;
  }
  const len = Math.floor(audioCtx.sampleRate * 0.05); // 50 ms is plenty
  const buf = audioCtx.createBuffer(1, len, audioCtx.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < len; i++) {
    data[i] = Math.random() * 2 - 1;
  }
  noiseBuffer = buf;
  return buf;
}

export function playStoneClick(): void {
  if (!enabled) return;
  const audio = getContext();
  if (!audio) return;
  // Browsers suspend the context until a user gesture — resume() is a
  // no-op if it's already running and silent on autoplay-blocked tabs.
  if (audio.state === "suspended") {
    void audio.resume().catch(() => undefined);
  }

  const now = audio.currentTime;
  const master = audio.createGain();
  master.gain.value = 0.55;
  master.connect(audio.destination);

  // ── Layer 1: filtered noise burst (the "snap")
  // High-passed white noise gated to ~25 ms so it sits as the attack
  // transient without blurring the pitched body underneath.
  const noise = audio.createBufferSource();
  noise.buffer = getNoiseBuffer(audio);
  const noiseHP = audio.createBiquadFilter();
  noiseHP.type = "highpass";
  noiseHP.frequency.value = 1800;
  noiseHP.Q.value = 0.7;
  const noiseGain = audio.createGain();
  noiseGain.gain.setValueAtTime(0.0001, now);
  noiseGain.gain.exponentialRampToValueAtTime(0.6, now + 0.001);
  noiseGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.025);
  noise.connect(noiseHP).connect(noiseGain).connect(master);
  noise.start(now);
  noise.stop(now + 0.06);

  // ── Layer 2: pitched body ("tock")
  // Triangle (richer than sine, less buzzy than square) at ~2.5 kHz with
  // tiny jitter per click so successive plays don't sound mechanical.
  const jitter = 1 + (Math.random() - 0.5) * 0.18; // ±9 %
  const osc = audio.createOscillator();
  osc.type = "triangle";
  osc.frequency.setValueAtTime(2500 * jitter, now);
  // Slight downward pitch slide ≈ wood-on-wood resonance damping.
  osc.frequency.exponentialRampToValueAtTime(1700 * jitter, now + 0.07);
  const oscGain = audio.createGain();
  oscGain.gain.setValueAtTime(0.0001, now);
  oscGain.gain.exponentialRampToValueAtTime(0.55, now + 0.003);
  oscGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.08);
  osc.connect(oscGain).connect(master);
  osc.start(now);
  osc.stop(now + 0.1);
}
