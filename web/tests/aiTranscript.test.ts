import assert from "node:assert/strict";
import test from "node:test";
import { roundTranscriptMessages } from "../src/lib/aiTranscript.ts";
import type { RoundState } from "../src/lib/voiceBackend.ts";

test("maps voice rounds to AI SDK messages and feedback tool parts", () => {
  const messages = roundTranscriptMessages({
    id: "round-1",
    persona: "technician",
    difficulty: "associate",
    score: 61,
    turn: 1,
    ladder: 1,
    runtime: "google_adk",
    messages: [
      { role: "opponent", text: "Explain your legal basis." },
      { role: "user", text: "The DPA needs processor controls." },
    ],
    events: [{ turn: 1, classification: "held_firm", points: 5, note: "Clear frame." }],
  } satisfies RoundState);

  assert.equal(messages[0].role, "assistant");
  assert.equal(messages[1].role, "user");
  assert.equal(messages[2].parts[0].type, "dynamic-tool");
  assert.equal(messages[2].parts[0].state, "output-available");
});

test("returns no messages before a backend round starts", () => {
  assert.deepEqual(roundTranscriptMessages(null), []);
});
