const STORAGE_KEY = "sfx:stone";
const SAMPLES = [
  "/sounds/stone-1.mp3",
  "/sounds/stone-2.mp3",
  "/sounds/stone-3.mp3",
];
const POOL_SIZE = 3;

let enabled = true;
let pool: HTMLAudioElement[] | null = null;
let cursor = 0;

if (typeof window !== "undefined") {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "0") enabled = false;
}

function getPool(): HTMLAudioElement[] | null {
  if (typeof window === "undefined") return null;
  if (pool) return pool;
  pool = [];
  for (let i = 0; i < POOL_SIZE; i++) {
    const a = new Audio(SAMPLES[i % SAMPLES.length]);
    a.volume = 0.7;
    a.preload = "auto";
    pool.push(a);
  }
  return pool;
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

export function playStoneClick(): void {
  if (!enabled) return;
  const p = getPool();
  if (!p) return;
  const sample = SAMPLES[Math.floor(Math.random() * SAMPLES.length)];
  // Round-robin across audio elements so rapid clicks don't cut each other off.
  const slot = p[cursor];
  cursor = (cursor + 1) % p.length;
  slot.pause();
  slot.currentTime = 0;
  if (slot.src !== window.location.origin + sample) {
    slot.src = sample;
  }
  void slot.play().catch(() => {
    // Browser refused autoplay (no user gesture yet) — silently ignore.
  });
}
