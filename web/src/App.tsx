import { useState } from "react";
import Arena from "./Arena";

// App-phase routing seam — only arena wired in Stage 0.
// Later stages fill: setup | debrief | progress
export type AppPhase = "setup" | "arena" | "debrief" | "progress";

export default function App() {
  const [phase, setPhase] = useState<AppPhase>("arena");
  const [roundId] = useState(() => `round-${Date.now()}`);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {phase === "arena" && (
        <Arena roundId={roundId} onRoundEnd={() => setPhase("debrief")} />
      )}
      {phase === "debrief" && (
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Round complete</h1>
            <button
              className="px-4 py-2 bg-indigo-600 rounded hover:bg-indigo-500"
              onClick={() => setPhase("arena")}
            >
              Run it again
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
