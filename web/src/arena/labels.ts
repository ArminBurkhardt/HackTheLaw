import type { MoveEvent } from "../lib/ws";

export const SCENARIO_LABELS: Record<string, string> = {
  negotiation: "SaaS Liability Negotiation",
  hot_seat: "Hot Seat",
  difficult_client: "Difficult Client",
};

export const PERSONA_LABELS: Record<string, string> = {
  aggressor: "The Aggressor",
  charmer: "The Charmer",
  stonewaller: "The Stonewaller",
  technician: "The Technician",
};

export const MOVE_EMOJI: Record<MoveEvent["classification"], string> = {
  good_move: "✅",
  held_firm: "🛡️",
  conceded_early: "🔴",
  missed_point: "❗",
  overplayed: "⚠️",
  neutral: "·",
};

export const MOVE_COLOR: Record<MoveEvent["classification"], string> = {
  good_move: "text-emerald-400",
  held_firm: "text-blue-400",
  conceded_early: "text-rose-400",
  missed_point: "text-amber-400",
  overplayed: "text-orange-400",
  neutral: "text-gray-500",
};

export function classificationLabel(c: MoveEvent["classification"]): string {
  return c.replace(/_/g, " ");
}
