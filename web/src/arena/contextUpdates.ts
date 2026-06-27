import type { RoundContext } from "../lib/ws";
import type { Message } from "./types";

export function applyContextUpdate(messages: Message[], context: RoundContext): Message[] {
  let next = context.last_move ? attachMoveEvent(messages, context.last_move) : messages;
  const reason = context.abort_reason;
  if (reason && !next.some((message) => message.text === abortText(reason))) {
    next = [...next, { role: "opponent", text: abortText(reason) }];
  }
  return next;
}

function attachMoveEvent(messages: Message[], moveEvent: NonNullable<RoundContext["last_move"]>): Message[] {
  let userTurn = 0;
  let changed = false;
  const next = messages.map((message) => {
    if (message.role !== "user") return message;
    userTurn += 1;
    if (userTurn !== moveEvent.turn || message.moveEvent) return message;
    changed = true;
    return { ...message, moveEvent };
  });
  return changed ? next : messages;
}

function abortText(reason: string): string {
  return `Round aborted: ${reason}`;
}
