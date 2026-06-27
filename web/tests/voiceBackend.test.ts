import assert from "node:assert/strict";
import test from "node:test";
import { createVoiceRound, submitVoiceTurn, toBackendDifficulty, toBackendPersona } from "../src/lib/voiceBackend.ts";

test("maps voice personas to backend personas", () => {
  assert.equal(toBackendPersona("difficult_client"), "aggressor");
  assert.equal(toBackendPersona("impatient_partner"), "stonewaller");
  assert.equal(toBackendPersona("regulator"), "technician");
});

test("maps voice difficulty to backend difficulty", () => {
  assert.equal(toBackendDifficulty("warmup"), "junior");
  assert.equal(toBackendDifficulty("live"), "associate");
  assert.equal(toBackendDifficulty("crossfire"), "partner");
});

test("creates a credential-backed backend round through the voice proxy", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (input, init) => {
    assert.equal(input, "/api/voice/api/rounds");
    assert.equal(init?.method, "POST");
    assert.equal(init?.body, JSON.stringify({ persona: "technician", difficulty: "partner" }));

    return Response.json({
      round: {
        id: "round-1",
        persona: "technician",
        difficulty: "partner",
        score: 50,
        turn: 0,
        ladder: 0,
        runtime: "google_adk",
        messages: [{ role: "opponent", text: "Opening" }],
        events: [],
      },
    });
  };

  const round = await createVoiceRound("regulator", "crossfire");

  assert.equal(round.runtime, "google_adk");
});

test("surfaces backend proxy errors", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async () => Response.json({ detail: "CRUCIBLE_API_BASE_URL is not configured." }, { status: 500 });

  await assert.rejects(
    () => submitVoiceTurn("round-1", "My spoken move"),
    /CRUCIBLE_API_BASE_URL/,
  );
});
