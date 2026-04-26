import "@testing-library/jest-dom";

// Provide a working localStorage shim so zustand/persist doesn't throw in jsdom.
// jsdom exposes a Storage object but its methods are on the prototype, which
// some environments (vitest's jsdom runner) can't access via direct property
// lookup. Replace it with a plain-object shim that always works.
{
  const store: Record<string, string> = {};
  const localStorageMock = {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
    clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
  };
  Object.defineProperty(globalThis, "localStorage", {
    value: localStorageMock,
    writable: true,
    configurable: true,
  });
}
