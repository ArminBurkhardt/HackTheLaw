import type { DynamicToolUIPart, TextUIPart, UIMessage } from "ai";
import type { Message, MoveEvent, RoundState } from "./voiceBackend";

export function roundTranscriptMessages(round: RoundState | null): UIMessage[] {
  if (!round) return [];

  return [
    ...round.messages.map((message, index) => roundTextMessage(message, index)),
    ...round.events.map((event) => feedbackMessage(event)),
  ];
}

function roundTextMessage(message: Message, index: number): UIMessage {
  return {
    id: `voice-message-${index}`,
    role: message.role === "user" ? "user" : "assistant",
    parts: [textPart(message.text)],
  };
}

function feedbackMessage(event: MoveEvent): UIMessage {
  return {
    id: `voice-feedback-${event.turn}`,
    role: "assistant",
    parts: [
      feedbackPart(event),
      textPart(event.note),
    ],
  };
}

function feedbackPart(event: MoveEvent): DynamicToolUIPart {
  return {
    type: "dynamic-tool",
    toolCallId: `voice-score-${event.turn}`,
    toolName: "voice_argument_evaluator",
    title: `Turn ${event.turn} feedback`,
    state: "output-available",
    input: { turn: event.turn, classification: event.classification },
    output: { points: event.points, note: event.note },
  };
}

function textPart(text: string): TextUIPart {
  return { type: "text", text, state: "done" };
}
