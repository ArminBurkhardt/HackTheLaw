export interface MoveEvent {
  turn: number;
  classification: "good_move" | "conceded_early" | "missed_point" | "overplayed" | "held_firm" | "neutral";
  refs: string[];
  position_delta: number;
  note: string;
}

export interface WsMessage {
  reply: string;
  move_event?: MoveEvent;
  current_position?: number;
  round_complete?: boolean;
}

export interface RoundContextSource {
  tool: string;
  title: string;
  url?: string | null;
  pinpoint?: string | null;
  snippet?: string;
}

export interface RoundContextTool {
  name: string;
  configured: boolean;
  status: "ok" | "error" | "not_configured";
  detail?: string;
}

export interface RoundContextHook {
  id: string;
  label: string;
  kind: string;
  target: string;
  authorities: Array<{ title: string; pinpoint?: string | null; celex?: string | null }>;
}

export interface RoundContext {
  scenario: string;
  persona: string;
  current_position: number;
  latest_user: string;
  latest_opponent: string;
  last_move: MoveEvent | null;
  hooks: RoundContextHook[];
  tools: RoundContextTool[];
  sources: RoundContextSource[];
}

export type WsHandler = (msg: WsMessage) => void;
export type WsErrorHandler = (err: Event) => void;

export function createRoundWs(
  roundId: string,
  onMessage: WsHandler,
  onError?: WsErrorHandler
): { send: (text: string) => void; close: () => void } {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/round/${roundId}/turn`);

  ws.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data) as WsMessage);
    } catch {
      // ignore malformed frames
    }
  };

  if (onError) ws.onerror = onError;

  return {
    send: (text: string) => ws.send(JSON.stringify({ message: text })),
    close: () => ws.close(),
  };
}

export async function startRound(
  roundId: string,
  scenario: string,
  persona: string,
  scoreToBeat: number | null = null
): Promise<void> {
  const res = await fetch(`/round/${roundId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, persona, mode: "playbook", score_to_beat: scoreToBeat }),
  });
  if (!res.ok) throw new Error(`Failed to start round: ${res.statusText}`);
}

export async function endRound(roundId: string): Promise<unknown> {
  const res = await fetch(`/round/${roundId}/end`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to end round: ${res.statusText}`);
  return res.json();
}

export async function fetchRoundContext(roundId: string): Promise<RoundContext> {
  const res = await fetch(`/round/${roundId}/context`);
  if (!res.ok) throw new Error(`Failed to fetch round context: ${res.statusText}`);
  return res.json();
}

export async function synthesizeLiveAudio(text: string, language = "en"): Promise<Blob> {
  const res = await fetch("/audio/live", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) {
    const body = await readJson(res);
    throw new Error(errorMessage(body, res.status));
  }
  return res.blob();
}

export async function fetchProgress(userId: string = "demo_user"): Promise<unknown> {
  const res = await fetch(`/progress/${encodeURIComponent(userId)}`);
  if (!res.ok) throw new Error(`Failed to fetch progress: ${res.statusText}`);
  return res.json();
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function errorMessage(body: unknown, status: number): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return `Live audio request failed with status ${status}.`;
}
