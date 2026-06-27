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

export async function fetchProgress(userId: string = "demo_user"): Promise<unknown> {
  const res = await fetch(`/progress/${encodeURIComponent(userId)}`);
  if (!res.ok) throw new Error(`Failed to fetch progress: ${res.statusText}`);
  return res.json();
}
