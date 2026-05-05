import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Match the subset of WebSocket the lib touches: send, close, readyState, onopen, onmessage, onclose.
// `static OPEN` mirrors the real WebSocket constant — code under test compares
// `ws.readyState === WebSocket.OPEN`, so the global stub must expose it too.
class FakeWS {
  static instances: FakeWS[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  url: string;
  readyState = 0; // CONNECTING
  onopen: (() => void) | null = null;
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
    this.onopen?.();
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

describe("openGameWS — outbound queue (P0-11)", () => {
  beforeEach(() => {
    FakeWS.instances = [];
    vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 200 }));
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("queues sends issued before the socket opens, then flushes on open in order", async () => {
    const { openGameWS } = await import("@/lib/ws");
    const handle = openGameWS(1, () => {});

    handle.send({ type: "hint" });
    handle.send({ type: "score" });

    // Still CONNECTING — nothing actually transmitted yet.
    expect(FakeWS.instances[0].sent).toEqual([]);

    FakeWS.instances[0].simulateOpen();

    expect(FakeWS.instances[0].sent).toEqual([
      JSON.stringify({ type: "hint" }),
      JSON.stringify({ type: "score" }),
    ]);
    handle.close();
  });

  it("queues sends during disconnect and flushes on reconnect", async () => {
    const { openGameWS } = await import("@/lib/ws");
    const handle = openGameWS(2, () => {});

    FakeWS.instances[0].simulateOpen();
    handle.send({ type: "a" });
    expect(FakeWS.instances[0].sent).toEqual([JSON.stringify({ type: "a" })]);

    FakeWS.instances[0].simulateClose();
    handle.send({ type: "b" });
    handle.send({ type: "c" });

    // After the 1.5s reconnect timer + probe, a fresh socket is created.
    await vi.advanceTimersByTimeAsync(1500);
    await flushMicrotasks();
    expect(FakeWS.instances).toHaveLength(2);

    FakeWS.instances[1].simulateOpen();

    expect(FakeWS.instances[1].sent).toEqual([
      JSON.stringify({ type: "b" }),
      JSON.stringify({ type: "c" }),
    ]);
    handle.close();
  });

  it("caps the pending queue and drops the oldest entries", async () => {
    const { openGameWS } = await import("@/lib/ws");
    const handle = openGameWS(3, () => {});

    // 50 messages issued while the socket is still CONNECTING.
    // The cap is 32; the oldest 18 should be dropped.
    for (let i = 0; i < 50; i++) {
      handle.send({ type: "noop", n: i });
    }

    FakeWS.instances[0].simulateOpen();

    expect(FakeWS.instances[0].sent).toHaveLength(32);
    expect(FakeWS.instances[0].sent[0]).toBe(
      JSON.stringify({ type: "noop", n: 18 }),
    );
    expect(FakeWS.instances[0].sent[31]).toBe(
      JSON.stringify({ type: "noop", n: 49 }),
    );
    handle.close();
  });

  it("drops queued messages when the caller closes explicitly", async () => {
    const { openGameWS } = await import("@/lib/ws");
    const handle = openGameWS(4, () => {});

    handle.send({ type: "queued-then-closed" });
    handle.close();

    // Even if the socket somehow opened after close(), nothing should ship.
    FakeWS.instances[0].simulateOpen();
    expect(FakeWS.instances[0].sent).toEqual([]);
  });
});
