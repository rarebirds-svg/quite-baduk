export type WSMessage =
  | { type: "state"; board: string; to_move: string; move_count: number; captures: Record<string, number> }
  | { type: "ai_move"; coord: string; captures: number }
  | { type: "game_over"; result: string; winner: string }
  | { type: "error"; code: string; detail?: string };

export interface GameWS {
  send(msg: unknown): void;
  close(): void;
}

export function openGameWS(
  gameId: number,
  onMessage: (m: WSMessage) => void
): GameWS {
  const base = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/^http/, "ws");
  const url = `${base}/api/ws/games/${gameId}`;
  let ws = new WebSocket(url);
  let closed = false;

  const handlers = () => {
    ws.onmessage = (ev) => {
      try {
        onMessage(JSON.parse(ev.data));
      } catch {}
    };
    ws.onclose = () => {
      if (closed) return;
      // simple retry
      setTimeout(() => {
        if (closed) return;
        ws = new WebSocket(url);
        handlers();
      }, 1500);
    };
  };

  handlers();

  return {
    send(msg) {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
    },
    close() {
      closed = true;
      ws.close();
    }
  };
}
