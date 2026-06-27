import { useCallback, useEffect, useRef, useState } from "react";
import Arena from "./Arena";
import ScenarioPicker from "./ScenarioPicker";
import Debrief from "./Debrief";
import Progress from "./Progress";
import Settings, { AppLanguage } from "./Settings";
import { startRound, endRound, fetchProgress, fetchRoundContext, RoundContext } from "./lib/ws";

export type AppPhase = "setup" | "settings" | "starting" | "arena" | "ending" | "debrief" | "progress";
export type AppTheme = "dark" | "light";

interface PreparedRound {
  key: string;
  roundId: string;
  context: RoundContext | null;
  startPromise?: Promise<PreparedRound>;
  contextPromise?: Promise<RoundContext | null>;
}

function makeRoundId() {
  return `round-${Date.now()}`;
}

function routeForPhase(phase: AppPhase): string {
  if (phase === "settings") return "/settings";
  if (phase === "progress") return "/profile";
  if (phase === "arena" || phase === "starting" || phase === "ending" || phase === "debrief") return "/arena";
  return "/";
}

function routePhase(pathname: string): AppPhase {
  if (pathname === "/settings") return "settings";
  if (pathname === "/profile") return "progress";
  if (pathname === "/arena") return "arena";
  return "setup";
}

export default function App() {
  const [phase, setPhaseState] = useState<AppPhase>(() => routePhase(window.location.pathname));
  const [progressBackPhase, setProgressBackPhase] = useState<AppPhase>("setup");
  const [roundId, setRoundId] = useState(makeRoundId);
  const preparedRoundRef = useRef<PreparedRound | null>(null);
  const [preparedRound, setPreparedRound] = useState<PreparedRound | null>(null);
  const [scoreToBeat, setScoreToBeat] = useState<number | null>(null);
  const [debriefData, setDebriefData] = useState<unknown>(null);
  const [progressData, setProgressData] = useState<unknown>(null);
  const [language, setLanguage] = useState<AppLanguage>(() => {
    const saved = window.localStorage.getItem("crucible_language");
    return saved === "de" ? "de" : "en";
  });
  const [theme, setTheme] = useState<AppTheme>(() => {
    const saved = window.localStorage.getItem("crucible_theme");
    return saved === "light" ? "light" : "dark";
  });
  const [error, setError] = useState<string | null>(null);
  const activeRoundRef = useRef(false);

  const setPhase = useCallback((nextPhase: AppPhase, historyMode: "push" | "replace" = "push") => {
    setPhaseState(nextPhase);
    const nextRoute = routeForPhase(nextPhase);
    if (window.location.pathname !== nextRoute) {
      window.history[historyMode === "replace" ? "replaceState" : "pushState"]({}, "", nextRoute);
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("theme-light", theme === "light");
    document.documentElement.classList.toggle("theme-dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    if (window.location.pathname === "/arena" && !activeRoundRef.current) {
      window.history.replaceState({}, "", "/");
      setPhaseState("setup");
    }
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      const nextPhase = routePhase(window.location.pathname);
      if (nextPhase === "arena" && !activeRoundRef.current) {
        window.history.replaceState({}, "", "/");
        setPhaseState("setup");
        return;
      }
      setPhaseState(nextPhase);
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const prepareRound = useCallback(
    (scenario: string, persona: string, hardness: string, beat: number | null): Promise<PreparedRound> => {
      const key = [scenario, persona, hardness, beat ?? "", language].join("|");
      const current = preparedRoundRef.current;
      if (current?.key === key) return current.startPromise ?? Promise.resolve(current);

      const id = makeRoundId();
      const pending: PreparedRound = { key, roundId: id, context: null };
      const startPromise = (async () => {
        await startRound(id, scenario, persona, hardness, beat, language);
        if (preparedRoundRef.current?.key === key && preparedRoundRef.current.roundId === id) {
          setPreparedRound({ ...pending });
        }
        return pending;
      })();

      const contextPromise = startPromise
        .then(() => fetchRoundContext(id))
        .then((context) => {
          if (preparedRoundRef.current?.key === key && preparedRoundRef.current.roundId === id) {
            const prepared = { ...pending, context };
            preparedRoundRef.current = prepared;
            setPreparedRound(prepared);
          }
          return context;
        })
        .catch((error) => {
          if (preparedRoundRef.current?.key === key && preparedRoundRef.current.roundId === id) {
            setError(error instanceof Error ? error.message : String(error));
          }
          return null;
        });

      pending.startPromise = startPromise;
      pending.contextPromise = contextPromise;
      preparedRoundRef.current = pending;
      setPreparedRound(pending);
      return startPromise;
    },
    [language]
  );

  const handlePrepare = useCallback(
    (scenario: string, persona: string, hardness: string, beat: number | null) => {
      const keyPrefix = [scenario, persona, hardness, beat ?? "", language].join("|");
      setError(null);
      void prepareRound(scenario, persona, hardness, beat).catch((e) => {
        if (preparedRoundRef.current?.key === keyPrefix) {
          preparedRoundRef.current = null;
          setPreparedRound(null);
        }
        setError(e instanceof Error ? e.message : String(e));
      });
    },
    [language, prepareRound]
  );

  const handleStart = useCallback(
    async (scenario: string, persona: string, hardness: string, beat: number | null) => {
      setError(null);
      setPhase("starting");
      try {
        const prepared = await prepareRound(scenario, persona, hardness, beat);
        activeRoundRef.current = true;
        setRoundId(prepared.roundId);
        setPhase("arena", "replace");
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setPhase("setup", "replace");
      }
    },
    [prepareRound, setPhase]
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
  }, [setPhase]);

  const handleRunAgain = useCallback(() => {
    activeRoundRef.current = false;
    preparedRoundRef.current = null;
    setPreparedRound(null);
    setPhase("setup");
    setDebriefData(null);
  }, [setPhase]);

  const handleViewProgress = useCallback(async () => {
    try {
      setProgressBackPhase(phase === "debrief" ? "debrief" : "setup");
      const data = await fetchProgress("demo_user");
      setProgressData(data);
      setPhase("progress");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [phase, setPhase]);

  useEffect(() => {
    if (phase === "progress" && !progressData) {
      void handleViewProgress();
    }
  }, [handleViewProgress, phase, progressData]);

  const handleProgressBack = useCallback(() => {
    setPhase(progressBackPhase);
  }, [progressBackPhase, setPhase]);

  const handleLanguageChange = useCallback((nextLanguage: AppLanguage) => {
    window.localStorage.setItem("crucible_language", nextLanguage);
    preparedRoundRef.current = null;
    setPreparedRound(null);
    setLanguage(nextLanguage);
  }, []);

  const handleThemeChange = useCallback((nextTheme: AppTheme) => {
    window.localStorage.setItem("crucible_theme", nextTheme);
    setTheme(nextTheme);
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
          onPrepare={(sc, pe, hardness) => handlePrepare(sc, pe, hardness, scoreToBeat)}
          onStart={(sc, pe, hardness) => handleStart(sc, pe, hardness, scoreToBeat)}
        />
      </>
    );
  }

  if (phase === "settings") {
    return (
      <Settings
        language={language}
        theme={theme}
        onLanguageChange={handleLanguageChange}
        onThemeChange={handleThemeChange}
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
        <Arena
          roundId={roundId}
          initialContext={preparedRound?.roundId === roundId ? preparedRound.context : null}
          initialContextPromise={preparedRound?.roundId === roundId ? preparedRound.contextPromise : null}
          language={language}
          onRoundEnd={handleRoundEnd}
        />
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

  if (phase === "progress") {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 text-sm animate-pulse">Loading profile…</div>
      </div>
    );
  }

  return null;
}
