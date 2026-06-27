import type { DynamicToolUIPart, TextUIPart, UIMessage } from "ai";
import type { Message, MoveEvent, RoundState } from "./voiceBackend";

export function roundTranscriptMessages(round: RoundState | null): UIMessage[] {
  if (!round) return [];

  return [
    ...roundConversationMessages(round),
    ...round.events.map((event) => feedbackMessage(event)),
  ];
}

export function roundConversationMessages(
  round: RoundState | null,
  pendingUserText = "",
  pendingAssistantText = "",
): UIMessage[] {
  if (!round) return [];
  const messages = round.messages.map((message, index) => roundTextMessage(message, index));
  const cleaned = pendingUserText.trim();
  const assistant = pendingAssistantText.trim();
  if (cleaned) {
    messages.push({
      id: "voice-message-pending-user",
      role: "user",
      parts: [textPart(cleaned)],
    });
  }
  if (assistant) {
    messages.push({
      id: "voice-message-pending-assistant",
      role: "assistant",
      parts: [textPart(assistant)],
    });
  }
  return messages;
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
