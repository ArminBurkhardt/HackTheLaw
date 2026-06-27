export interface MoveEvent {
  turn: number;
  classification: "good_move" | "conceded_early" | "missed_point" | "overplayed" | "held_firm" | "neutral";
  refs: string[];
  position_delta: number;
  note: string;
}

export interface LiveUtterance {
  reply: string;
  transcript: string;
  audio_base64: string;
  mime_type: string;
}

export interface LiveTurnMessage extends LiveUtterance {
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

export async function startRound(
  roundId: string,
  scenario: string,
  persona: string,
  hardness: string,
  scoreToBeat: number | null = null,
  language = "en"
): Promise<void> {
  const res = await fetch(`/round/${roundId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, persona, hardness, mode: "playbook", score_to_beat: scoreToBeat, language }),
  });
  if (!res.ok) throw new Error(`Failed to start round: ${res.statusText}`);
}

export async function endRound(roundId: string): Promise<unknown> {
  const res = await fetch(`/round/${roundId}/end`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to end round: ${res.statusText}`);
  return res.json();
}

export async function fetchOpeningLiveTurn(roundId: string, language = "en"): Promise<LiveUtterance> {
  const res = await fetch(`/round/${roundId}/opening/live`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language }),
  });
  if (!res.ok) {
    const body = await readJson(res);
    throw new Error(errorMessage(body, res.status));
  }
  return res.json();
}

export async function sendLiveTurn(
  roundId: string,
  message: string,
  language = "en"
): Promise<LiveTurnMessage> {
  const res = await fetch(`/round/${roundId}/turn/live`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, language }),
  });
  if (!res.ok) {
    const body = await readJson(res);
    throw new Error(errorMessage(body, res.status));
  }
  return res.json();
}

export async function fetchRoundContext(roundId: string): Promise<RoundContext> {
  const res = await fetch(`/round/${roundId}/context`);
  if (!res.ok) throw new Error(`Failed to fetch round context: ${res.statusText}`);
  return res.json();
}

export function audioBlobFromBase64(data: string, mimeType = "audio/wav"): Blob {
  const binary = atob(data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mimeType });
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
