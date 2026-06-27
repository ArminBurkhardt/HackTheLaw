import { useState, useCallback } from "react";
import Arena from "./Arena";
import ScenarioPicker from "./ScenarioPicker";
import Debrief from "./Debrief";
import Progress from "./Progress";
import Settings, { AppLanguage } from "./Settings";
import { startRound, endRound, fetchProgress } from "./lib/ws";

export type AppPhase = "setup" | "settings" | "starting" | "arena" | "ending" | "debrief" | "progress";

function makeRoundId() {
  return `round-${Date.now()}`;
}

export default function App() {
  const [phase, setPhase] = useState<AppPhase>("setup");
  const [progressBackPhase, setProgressBackPhase] = useState<AppPhase>("setup");
  const [roundId, setRoundId] = useState(makeRoundId);
  const [scoreToBeat, setScoreToBeat] = useState<number | null>(null);
  const [debriefData, setDebriefData] = useState<unknown>(null);
  const [progressData, setProgressData] = useState<unknown>(null);
  const [language, setLanguage] = useState<AppLanguage>(() => {
    const saved = window.localStorage.getItem("crucible_language");
    return saved === "de" ? "de" : "en";
  });
  const [error, setError] = useState<string | null>(null);

  const handleStart = useCallback(
    async (scenario: string, persona: string, hardness: string, beat: number | null) => {
      const id = makeRoundId();
      setRoundId(id);
      setError(null);
      setPhase("starting");
      try {
        await startRound(id, scenario, persona, hardness, beat, language);
        setPhase("arena");
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setPhase("setup");
      }
    },
    [language]
  );

  const handleRoundEnd = useCallback(async (id: string) => {
    setError(null);
    setPhase("ending");
    try {
      const result = await endRound(id);
      setDebriefData(result);
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

  const handleViewProgress = useCallback(async () => {
    try {
      setProgressBackPhase(phase === "debrief" ? "debrief" : "setup");
      const data = await fetchProgress("demo_user");
      setProgressData(data);
      setPhase("progress");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [phase]);

  const handleProgressBack = useCallback(() => {
    setPhase(progressBackPhase);
  }, [progressBackPhase]);

  const handleLanguageChange = useCallback((nextLanguage: AppLanguage) => {
    window.localStorage.setItem("crucible_language", nextLanguage);
    setLanguage(nextLanguage);
  }, []);

  if (phase === "setup") {
    return (
      <>
        {error && (
          <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-rose-900 text-rose-100 px-4 py-2 rounded-lg text-sm z-50">
            {error}
          </div>
        )}
        <ScenarioPicker
          language={language}
          onSettings={() => setPhase("settings")}
          onViewProgress={handleViewProgress}
          onStart={(sc, pe, hardness) => handleStart(sc, pe, hardness, scoreToBeat)}
        />
      </>
    );
  }

  if (phase === "settings") {
    return (
      <Settings
        language={language}
        onLanguageChange={handleLanguageChange}
        onViewProgress={handleViewProgress}
        onBack={() => setPhase("setup")}
      />
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
    return (
      <>
        {error && (
          <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-rose-900 text-rose-100 px-4 py-2 rounded-lg text-sm z-50 shadow-lg">
            Could not generate the debrief: {error}
          </div>
        )}
        <Arena roundId={roundId} language={language} onRoundEnd={handleRoundEnd} />
      </>
    );
  }

  if (phase === "debrief" && debriefData) {
    const data = (debriefData as { debrief?: unknown })?.debrief ?? debriefData;
    return (
      <Debrief
        debrief={data as Parameters<typeof Debrief>[0]["debrief"]}
        onRunAgain={handleRunAgain}
        onViewProgress={handleViewProgress}
      />
    );
  }

  if (phase === "progress" && progressData) {
    return (
      <Progress
        data={progressData as Parameters<typeof Progress>[0]["data"]}
        scoreToBeat={scoreToBeat}
        onBack={handleProgressBack}
      />
    );
  }

  return null;
}
