export interface ScoreResultMsg {
  type: "score_result";
  black_territory: number;
  white_territory: number;
  black_captures: number;
  white_captures: number;
  komi: number;
  black_score: number;
  white_score: number;
  winner: string; // "B" | "W"
  margin: number;
  result: string;
  reason?: "ai_passed";
  black_points: [number, number][];
  white_points: [number, number][];
  dame_points: [number, number][];
  dead_stones: [number, number][];
}

export type WSMessage =
  | {
      type: "state";
      board: string;
      board_size: number;
      to_move: string;
      move_count: number;
      captures: Record<string, number>;
      winrate_black?: number;
      undo_count?: number;
      score_lead_black?: number;
      endgame_phase?: boolean;
    }
  | { type: "ai_move"; coord: string; captures: number }
  | { type: "winrate"; winrate_black: number; score_lead_black?: number }
  | { type: "game_over"; result: string; winner: string; reason?: "ai_resigned" | "user_resigned" }
  | ScoreResultMsg
  | { type: "error"; code: string; detail?: string };

export interface GameWS {
  send(msg: unknown): void;
  close(): void;
}

export function openGameWS(
  gameId: number,
  onMessage: (m: WSMessage) => void
): GameWS {
  // Prefer same-origin in the browser so the WS rides the same host as the
  // page (works through tunnels, LAN access, and prod behind a reverse proxy
  // that forwards /api/ws to the backend). Falls back to NEXT_PUBLIC_API_URL
  // for server-side / non-window contexts.
  const base =
    typeof window !== "undefined"
      ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`
      : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(
          /^http/,
          "ws",
        );
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
