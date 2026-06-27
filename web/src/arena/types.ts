import type { MoveEvent, RoundContext } from "../lib/ws";

export interface Message {
  role: "user" | "opponent";
  text: string;
  moveEvent?: MoveEvent;
}

export interface ArenaProps {
  roundId: string;
  initialContext?: RoundContext | null;
  initialContextPromise?: Promise<RoundContext | null> | null;
  language: "en" | "de";
  onRoundEnd: (roundId: string) => void;
}

export type AudioStatus = "idle" | "generating" | "speaking";
