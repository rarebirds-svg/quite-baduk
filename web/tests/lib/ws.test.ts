import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Match the subset of WebSocket the lib touches: send, close, readyState, onmessage, onclose.
class FakeWS {
  static instances: FakeWS[] = [];
  url: string;
  readyState = 0; // CONNECTING
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  sent: string[] = [];

  constructor(url: string) {
    this.url = url;
    FakeWS.instances.push(this);
    // Stay CONNECTING until simulateOpen() — keeps tests deterministic.
  }

  simulateOpen() {
    this.readyState = 1; // OPEN
  }
  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
  simulateClose() {
    this.readyState = 3; // CLOSED
    this.onclose?.();
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.simulateClose();
  }
}

const flushMicrotasks = async () => {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
};

describe("openGameWS — auth-lost handling", () => {
  beforeEach(() => {
    FakeWS.instances = [];
    vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("retries reconnect when probe says session is still valid", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ status: 200 });
    vi.stubGlobal("fetch", fetchMock);
    const onAuthLost = vi.fn();
    const { openGameWS } = await import("@/lib/ws");

    const handle = openGameWS(7, () => {}, { onAuthLost });
    expect(FakeWS.instances).toHaveLength(1);

    FakeWS.instances[0].simulateClose();
    // Run the 1.5s retry timer; the probe lives inside the timer callback.
    await vi.advanceTimersByTimeAsync(1500);
    await flushMicrotasks();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/7",
      expect.objectContaining({ credentials: "same-origin" }),
    );
    expect(onAuthLost).not.toHaveBeenCalled();
    expect(FakeWS.instances).toHaveLength(2); // reconnected
    handle.close();
  });

  it.each([401, 403, 404])(
    "stops retrying and fires onAuthLost when probe returns %i",
    async (status) => {
      const fetchMock = vi.fn().mockResolvedValue({ status });
      vi.stubGlobal("fetch", fetchMock);
      const onAuthLost = vi.fn();
      const { openGameWS } = await import("@/lib/ws");

      const handle = openGameWS(11, () => {}, { onAuthLost });
      FakeWS.instances[0].simulateClose();
      await vi.advanceTimersByTimeAsync(1500);
      await flushMicrotasks();

      expect(onAuthLost).toHaveBeenCalledTimes(1);
      expect(FakeWS.instances).toHaveLength(1); // no reconnect
      // Subsequent timer ticks don't spawn new sockets either.
      await vi.advanceTimersByTimeAsync(5000);
      expect(FakeWS.instances).toHaveLength(1);
      handle.close();
    },
  );

  it("retries when probe itself fails (network blip)", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("network"));
    vi.stubGlobal("fetch", fetchMock);
    const onAuthLost = vi.fn();
    const { openGameWS } = await import("@/lib/ws");

    const handle = openGameWS(3, () => {}, { onAuthLost });
    FakeWS.instances[0].simulateClose();
    await vi.advanceTimersByTimeAsync(1500);
    await flushMicrotasks();

    expect(onAuthLost).not.toHaveBeenCalled();
    expect(FakeWS.instances).toHaveLength(2);
    handle.close();
  });

  it("external close() suppresses reconnect even if probe would say 200", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ status: 200 });
    vi.stubGlobal("fetch", fetchMock);
    const { openGameWS } = await import("@/lib/ws");

    const handle = openGameWS(2, () => {});
    handle.close(); // marks closed before any reconnect can fire
    await vi.advanceTimersByTimeAsync(5000);
    await flushMicrotasks();

    expect(FakeWS.instances).toHaveLength(1);
  });
});
