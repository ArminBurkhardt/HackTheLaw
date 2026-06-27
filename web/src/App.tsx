import { useState, useCallback } from "react";
import Arena from "./Arena";
import ScenarioPicker from "./ScenarioPicker";
import Debrief from "./Debrief";
import { startRound, endRound } from "./lib/ws";

export type AppPhase = "setup" | "starting" | "arena" | "ending" | "debrief" | "progress";

function makeRoundId() {
  return `round-${Date.now()}`;
}

export default function App() {
  const [phase, setPhase] = useState<AppPhase>("setup");
  const [roundId, setRoundId] = useState(makeRoundId);
  const [scoreToBeat, setScoreToBeat] = useState<number | null>(null);
  const [debriefData, setDebriefData] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  const handleStart = useCallback(
    async (scenario: string, persona: string, beat: number | null) => {
      const id = makeRoundId();
      setRoundId(id);
      setError(null);
      setPhase("starting");
      try {
        await startRound(id, scenario, persona, beat);
        setPhase("arena");
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setPhase("setup");
      }
    },
    []
  );

  const handleRoundEnd = useCallback(async (id: string) => {
    setPhase("ending");
    try {
      const result = await endRound(id);
      setDebriefData(result);
      // Extract score for "run it again" targeting
      const score = (result as { debrief?: { score?: number } })?.debrief?.score ?? null;
      setScoreToBeat(score);
      setPhase("debrief");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("arena");
    }
  }, []);

  const handleRunAgain = useCallback(() => {
    setPhase("setup");
    setDebriefData(null);
  }, []);

  if (phase === "setup") {
    return (
      <>
        {error && (
          <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-rose-900 text-rose-100 px-4 py-2 rounded-lg text-sm z-50">
            {error}
          </div>
        )}
        <ScenarioPicker onStart={(sc, pe) => handleStart(sc, pe, scoreToBeat)} />
      </>
    );
  }

  if (phase === "starting" || phase === "ending") {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 text-sm animate-pulse">
          {phase === "starting" ? "Entering the arena…" : "Generating debrief…"}
        </div>
      </div>
    );
  }

  if (phase === "arena") {
    return <Arena roundId={roundId} onRoundEnd={handleRoundEnd} />;
  }

  if (phase === "debrief" && debriefData) {
    // The endpoint returns a TurnResult; the Debrief is nested inside it.
    // Fallback: if the endpoint returns the Debrief directly (non-WS path), unwrap.
    const data = (debriefData as { debrief?: unknown })?.debrief ?? debriefData;
    return <Debrief debrief={data as Parameters<typeof Debrief>[0]["debrief"]} onRunAgain={handleRunAgain} />;
  }

  return null;
}
