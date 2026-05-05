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
  // Row-major ownership read (length board_size**2, [-1, 1]). Surfaced so
  // the score-result sheet can render an optional heatmap; empty when the
  // server skipped the analysis (older clients also tolerate absence).
  ownership?: number[];
}

export interface EstimateResultMsg {
  type: "estimate_result";
  winrate_black: number;        // [0, 1] Black's perspective
  score_lead_black: number;     // signed: positive = Black ahead
  ownership: number[];          // row-major board_size**2, [-1, 1]
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
  | EstimateResultMsg
  | { type: "error"; code: string; detail?: string };

export interface GameWS {
  send(msg: unknown): void;
  close(): void;
}

export interface OpenGameWSOptions {
  /**
   * Fired when the WS keeps closing because the user no longer has access
   * to this game (session purged, evicted, or the game itself is gone).
   * Detected by probing /api/games/{id} for 401/403/404 before each retry.
   * The retry loop stops once this fires; the caller is expected to clear
   * its session state and route the user back to the login screen.
   */
  onAuthLost?: () => void;
}

export function openGameWS(
  gameId: number,
  onMessage: (m: WSMessage) => void,
  options: OpenGameWSOptions = {},
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
  const probeUrl = `/api/games/${gameId}`;
  let ws = new WebSocket(url);
  let closed = false;

  // P0-11: outbound queue. Any send() while the socket isn't OPEN is
  // buffered and flushed once the (re)connection settles. Capped so a
  // long disconnect can't accumulate without bound; oldest is dropped
  // first because the freshest game intent (latest hint/score request)
  // is what the user actually still expects to see honored.
  const PENDING_LIMIT = 32;
  const pending: string[] = [];

  const flushPending = () => {
    while (pending.length > 0 && ws.readyState === WebSocket.OPEN) {
      ws.send(pending.shift()!);
    }
  };

  const handlers = () => {
    ws.onopen = () => flushPending();
    ws.onmessage = (ev) => {
      try {
        onMessage(JSON.parse(ev.data));
      } catch {}
    };
    ws.onclose = () => {
      if (closed) return;
      setTimeout(async () => {
        if (closed) return;
        // Probe before reconnecting: if the user's session is gone or this
        // game no longer belongs to them, stop hammering the server and let
        // the caller surface the error. Network failures fall through to
        // the normal retry — they're usually transient.
        try {
          const r = await fetch(probeUrl, { credentials: "same-origin" });
          if (r.status === 401 || r.status === 403 || r.status === 404) {
            closed = true;
            options.onAuthLost?.();
            return;
          }
        } catch {
          // probe failed — assume transient and retry
        }
        if (closed) return;
        ws = new WebSocket(url);
        handlers();
      }, 1500);
    };
  };

  handlers();

  return {
    send(msg) {
      const data = JSON.stringify(msg);
      if (!closed && ws.readyState === WebSocket.OPEN) {
        ws.send(data);
        return;
      }
      if (closed) return;
      pending.push(data);
      while (pending.length > PENDING_LIMIT) pending.shift();
    },
    close() {
      closed = true;
      pending.length = 0;
      ws.close();
    }
  };
}
