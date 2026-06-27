import assert from "node:assert/strict";
import test from "node:test";
import { createSession, endSession, evaluateSpokenMove, playVoiceTurn } from "../src/lib/voiceTrainer.ts";

test("clear advice scores when recommendation, risk, and next step are present", () => {
  const event = evaluateSpokenMove(
    "I recommend we do not sign until the breach risk is documented and the next condition is accepted.",
    1,
    "live",
  );

  assert.equal(event.kind, "clear_advice");
  assert.ok(event.points > 0);
});

test("unsafe reassurance is penalized", () => {
  const event = evaluateSpokenMove("It is probably fine; we can ignore the issue.", 1, "crossfire");

  assert.equal(event.kind, "unsafe");
  assert.ok(event.points < -15);
});

test("session debrief reflects best moment", () => {
  const session = playVoiceTurn(
    createSession("impatient_partner", "warmup"),
    "I recommend we pause because the breach risk is not documented, then set the next condition.",
  );
  const debrief = endSession(session);

  assert.ok(debrief.score > 60);
  assert.match(debrief.bestMoment, /Turn 1/);
});
