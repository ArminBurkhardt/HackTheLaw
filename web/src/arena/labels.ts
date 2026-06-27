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

// chess.com-style move-quality glyphs (served from web/public/icons)
export const MOVE_ICON: Record<MoveEvent["classification"], string> = {
  good_move: "/icons/1_great.png",
  held_firm: "/icons/2_best.png",
  neutral: "/icons/5_book.png",
  missed_point: "/icons/9_missed_win.png",
  overplayed: "/icons/6_inaccuracy.png",
  conceded_early: "/icons/8_blunder.png",
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
