import assert from "node:assert/strict";
import test from "node:test";
import {
  createVoiceRound,
  getArgumentOptions,
  getBackendHealth,
  submitVoiceTurn,
  submitVoiceTurnStream,
  synthesizeLiveAudio,
  toBackendDifficulty,
  toBackendPersona,
} from "../src/lib/voiceBackend.ts";

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

test("loads backend health through the voice proxy", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (input, init) => {
    assert.equal(input, "/api/voice/health");
    assert.equal(init?.method, "GET");

    return Response.json({ status: "ok", configured: true, runtime: "google_adk" });
  };

  const health = await getBackendHealth();

  assert.equal(health.configured, true);
  assert.equal(health.runtime, "google_adk");
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

test("streams turn deltas and returns final round state", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (input, init) => {
    assert.equal(input, "/api/voice/api/rounds/round-1/turns/stream");
    assert.equal(init?.method, "POST");

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('{"type":"delta","text":"First "}\n'));
        controller.enqueue(encoder.encode('{"type":"delta","text":"chunk"}\n'));
        controller.enqueue(encoder.encode(JSON.stringify({
          type: "final",
          event: { turn: 1, classification: "held_firm", points: 6, note: "Clear." },
          round: {
            id: "round-1",
            persona: "aggressor",
            difficulty: "associate",
            score: 56,
            turn: 1,
            ladder: 0,
            runtime: "google_adk",
            messages: [
              { role: "opponent", text: "Opening" },
              { role: "user", text: "Move" },
              { role: "opponent", text: "First chunk" },
            ],
            events: [],
          },
        }) + "\n"));
        controller.close();
      },
    });
    return new Response(stream, { headers: { "content-type": "application/x-ndjson" } });
  };

  const deltas: string[] = [];
  const result = await submitVoiceTurnStream("round-1", "Move", (delta) => deltas.push(delta));

  assert.deepEqual(deltas, ["First ", "chunk"]);
  assert.equal(result.round.messages.at(-1)?.text, "First chunk");
});

test("loads generated argument options through the voice proxy", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (input, init) => {
    assert.equal(input, "/api/voice/api/rounds/round-1/argument-options");
    assert.equal(init?.method, "GET");

    return Response.json({
      options: [
        { label: "Hook", move: "Use Article 28.", rationale: "Names authority." },
        { label: "Limit", move: "Limit cadence.", rationale: "Controls burden." },
        { label: "Trade", move: "Ask for records.", rationale: "Keeps leverage." },
      ],
      tools_used: ["neo4j_cellar"],
      sources: [{ title: "CELLAR node", snippet: "GDPR Article 28" }],
      grounding_note: "Grounded on demand with neo4j_cellar.",
    });
  };

  const payload = await getArgumentOptions("round-1");

  assert.equal(payload.options.length, 3);
  assert.equal(payload.options[0].label, "Hook");
  assert.equal(payload.tools_used[0], "neo4j_cellar");
  assert.equal(payload.sources[0].title, "CELLAR node");
});

test("loads Gemini Live audio through the voice proxy", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  globalThis.fetch = async (input, init) => {
    assert.equal(input, "/api/voice/api/live-audio");
    assert.equal(init?.method, "POST");
    assert.equal(init?.body, JSON.stringify({ text: "Opponent reply" }));

    return new Response(new Blob(["wav"], { type: "audio/wav" }), {
      headers: { "content-type": "audio/wav" },
    });
  };

  const audio = await synthesizeLiveAudio("Opponent reply");

  assert.equal(audio.type, "audio/wav");
});
