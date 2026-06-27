import type { MoveEvent } from "../lib/ws";

export interface Message {
  role: "user" | "opponent";
  text: string;
  moveEvent?: MoveEvent;
}

export interface ArenaProps {
  roundId: string;
  language: "en" | "de";
  onRoundEnd: (roundId: string) => void;
}

export type AudioStatus = "idle" | "generating" | "speaking";
