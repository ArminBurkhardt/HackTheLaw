export type Persona = "difficult_client" | "impatient_partner" | "regulator";
export type Difficulty = "warmup" | "live" | "crossfire";
export type Role = "user" | "sparring";
export type MoveKind = "clear_advice" | "hedged" | "unsafe" | "empathetic" | "missed_risk";

export type Message = {
  role: Role;
  text: string;
};

export type VoiceEvent = {
  turn: number;
  kind: MoveKind;
  points: number;
  note: string;
};

export type SessionState = {
  persona: Persona;
  difficulty: Difficulty;
  score: number;
  turn: number;
  messages: Message[];
  events: VoiceEvent[];
};

export type SessionDebrief = {
  score: number;
  summary: string;
  bestMoment: string;
  nextDrill: string;
};

const openers: Record<Persona, string> = {
  difficult_client:
    "I do not want a long legal lecture. Can we just keep using the vendor and deal with the risk if it happens?",
  impatient_partner:
    "Give me the answer in thirty seconds. Can the client sign this DPA today or not?",
  regulator:
    "Your position sounds convenient. Explain the safeguards and the residual risk without hiding behind jargon.",
};

export function createSession(
  persona: Persona = "difficult_client",
  difficulty: Difficulty = "live",
): SessionState {
  return {
    persona,
    difficulty,
    score: 50,
    turn: 0,
    messages: [{ role: "sparring", text: openers[persona] }],
    events: [],
  };
}

export function playVoiceTurn(state: SessionState, text: string): SessionState {
  const event = evaluateSpokenMove(text, state.turn + 1, state.difficulty);
  const reply = sparringReply(event, state.persona);

  return {
    ...state,
    turn: state.turn + 1,
    score: clamp(state.score + event.points),
    messages: [...state.messages, { role: "user", text }, { role: "sparring", text: reply }],
    events: [...state.events, event],
  };
}

export function evaluateSpokenMove(
  text: string,
  turn: number,
  difficulty: Difficulty,
): VoiceEvent {
  const input = text.toLowerCase();
  const clear = input.includes("recommend") || input.includes("should") || input.includes("must");
  const risk = input.includes("risk") || input.includes("breach") || input.includes("liability");
  const action = input.includes("next") || input.includes("document") || input.includes("condition");
  const empathy = input.includes("understand") || input.includes("commercial") || input.includes("pressure");
  const unsafe = input.includes("ignore") || input.includes("probably fine") || input.includes("no issue");
  const penalty = difficulty === "crossfire" ? 4 : difficulty === "live" ? 2 : 0;

  if (unsafe) return event(turn, "unsafe", -16 - penalty, "You minimized risk instead of giving defensible advice.");
  if (clear && risk && action) {
    return event(turn, "clear_advice", 14 - penalty, "Clear recommendation, risk, and next step landed together.");
  }
  if (empathy && risk) return event(turn, "empathetic", 8 - penalty, "You kept the relationship while naming the risk.");
  if (!risk) return event(turn, "missed_risk", -8 - penalty, "The answer did not make the legal risk explicit.");
  return event(turn, "hedged", -3 - penalty, "The advice was legally relevant but not decisive enough.");
}

export function endSession(state: SessionState): SessionDebrief {
  const best =
    [...state.events].sort((a, b) => b.points - a.points)[0] ??
    event(0, "hedged", 0, "No spoken moves were captured.");

  return {
    score: state.score,
    summary:
      state.score >= 75
        ? "You gave advice that a client can act on."
        : "The conversation needs a firmer recommendation and clearer risk framing.",
    bestMoment: best.turn ? `Turn ${best.turn}: ${best.note}` : best.note,
    nextDrill:
      "Use the 20-second structure: recommendation, legal risk, commercial path, documented next step.",
  };
}

function sparringReply(event: VoiceEvent, persona: Persona): string {
  if (event.kind === "clear_advice") {
    return "That is actionable. I still want the shortest version I can repeat to the business team.";
  }

  const push =
    event.kind === "unsafe"
      ? "That is exactly the kind of answer that creates unmanaged risk."
      : "You are circling the issue. I need a decision, not atmosphere.";

  if (persona === "impatient_partner") return `${push} Give me the recommendation first.`;
  if (persona === "regulator") return `${push} Identify the safeguard and the residual risk.`;
  return `${push} Tell me what I should do next.`;
}

function event(turn: number, kind: MoveKind, points: number, note: string): VoiceEvent {
  return { turn, kind, points, note };
}

function clamp(score: number): number {
  return Math.max(0, Math.min(100, score));
}
