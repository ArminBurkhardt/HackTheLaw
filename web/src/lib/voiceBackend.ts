export type VoicePersona = "difficult_client" | "impatient_partner" | "regulator";
export type VoiceDifficulty = "warmup" | "live" | "crossfire";
export type BackendPersona = "aggressor" | "charmer" | "stonewaller" | "technician";
export type BackendDifficulty = "junior" | "associate" | "partner";
export type Role = "user" | "opponent";

export type Message = {
  role: Role;
  text: string;
};

export type MoveEvent = {
  turn: number;
  classification: string;
  points: number;
  note: string;
};

export type RoundState = {
  id: string;
  persona: BackendPersona;
  difficulty: BackendDifficulty;
  score: number;
  turn: number;
  ladder: number;
  messages: Message[];
  events: MoveEvent[];
  runtime: string;
};

export type Debrief = {
  score: number;
  headline: string;
  turning_point: string;
  stronger_move: string;
  next_run_focus: string;
  argument_reviews: ArgumentReview[];
};

export type ArgumentReview = {
  turn: number;
  verdict: string;
  quote: string;
  feedback: string;
};

export type ArgumentOption = {
  label: string;
  move: string;
  rationale: string;
};

export type GroundingSource = {
  title: string;
  url?: string | null;
  snippet?: string | null;
};

export type ArgumentOptionsPayload = {
  options: ArgumentOption[];
  tools_used: string[];
  sources: GroundingSource[];
  grounding_note: string;
};

export type BackendHealth = {
  status: string;
  configured: boolean;
  runtime: string;
  detail?: string;
};

type RoundPayload = { round: RoundState };
type TurnPayload = RoundPayload & { event: MoveEvent };
type DebriefPayload = { debrief: Debrief };

const personaMap: Record<VoicePersona, BackendPersona> = {
  difficult_client: "aggressor",
  impatient_partner: "stonewaller",
  regulator: "technician",
};

const difficultyMap: Record<VoiceDifficulty, BackendDifficulty> = {
  warmup: "junior",
  live: "associate",
  crossfire: "partner",
};

export function toBackendPersona(persona: VoicePersona): BackendPersona {
  return personaMap[persona];
}

export function toBackendDifficulty(difficulty: VoiceDifficulty): BackendDifficulty {
  return difficultyMap[difficulty];
}

export async function getBackendHealth(): Promise<BackendHealth> {
  return requestJson<BackendHealth>("/api/voice/health", { method: "GET" });
}

export async function createVoiceRound(
  persona: VoicePersona,
  difficulty: VoiceDifficulty,
): Promise<RoundState> {
  const payload = await requestJson<RoundPayload>("/api/voice/api/rounds", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      persona: toBackendPersona(persona),
      difficulty: toBackendDifficulty(difficulty),
    }),
  });
  return payload.round;
}

export async function submitVoiceTurn(roundId: string, text: string): Promise<TurnPayload> {
  return requestJson<TurnPayload>(`/api/voice/api/rounds/${roundId}/turns`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export async function endVoiceRound(roundId: string): Promise<Debrief> {
  const payload = await requestJson<DebriefPayload>(`/api/voice/api/rounds/${roundId}/end`, {
    method: "POST",
  });
  return payload.debrief;
}

export async function getArgumentOptions(roundId: string): Promise<ArgumentOptionsPayload> {
  return requestJson<ArgumentOptionsPayload>(`/api/voice/api/rounds/${roundId}/argument-options`, {
    method: "GET",
  });
}

export async function synthesizeLiveAudio(text: string): Promise<Blob> {
  const response = await fetch("/api/voice/api/live-audio", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const body = await readBody(response);
    throw new Error(errorMessage(body, response.status));
  }
  return response.blob();
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = await readBody(response);
  if (!response.ok) throw new Error(errorMessage(body, response.status));
  return body as T;
}

async function readBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function errorMessage(body: unknown, status: number): string {
  if (isRecord(body)) {
    if (typeof body.detail === "string") return body.detail;
    if (typeof body.message === "string") return body.message;
  }
  return `Voice backend request failed with status ${status}.`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
