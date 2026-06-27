import { useState } from "react";

interface Props {
  onStart: (scenario: string, persona: string, scoreToBeat: number | null) => void;
}

const SCENARIOS = [
  {
    id: "negotiation",
    label: "Contract Negotiation",
    description: "Negotiate a GDPR Data Processing Agreement clause-by-clause.",
    available: true,
  },
  {
    id: "hot_seat",
    label: "Hot Seat",
    description: "Defend your position under rapid-fire cross-examination.",
    available: false,
  },
  {
    id: "difficult_client",
    label: "Difficult Client",
    description: "Advise an unreasonable client who resists your guidance.",
    available: false,
  },
];

const PERSONAS = [
  {
    id: "aggressor",
    label: "The Aggressor",
    description: "Deadline-obsessed, ultimatum-prone, exploits every hesitation.",
    available: true,
  },
  {
    id: "charmer",
    label: "The Charmer",
    description: "Warm and collegial — dangerous because you lower your guard.",
    available: false,
  },
  {
    id: "stonewaller",
    label: "The Stonewaller",
    description: "Monosyllabic and immovable. Waits you out.",
    available: false,
  },
  {
    id: "technician",
    label: "The Technician",
    description: "Buries you in clause numbers and recital references.",
    available: false,
  },
];

type Step = "scenario" | "persona" | "confirm";

export default function ScenarioPicker({ onStart }: Props) {
  const [step, setStep] = useState<Step>("scenario");
  const [scenario, setScenario] = useState("negotiation");
  const [persona, setPersona] = useState("aggressor");

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-2xl">
        {/* Progress pills */}
        <div className="flex gap-2 mb-10">
          {(["scenario", "persona", "confirm"] as Step[]).map((s, i) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors ${
                step === s
                  ? "bg-indigo-500"
                  : i < ["scenario", "persona", "confirm"].indexOf(step)
                  ? "bg-indigo-800"
                  : "bg-gray-700"
              }`}
            />
          ))}
        </div>

        {step === "scenario" && (
          <>
            <h1 className="text-2xl font-bold mb-2">Choose your scenario</h1>
            <p className="text-gray-400 text-sm mb-6">What kind of legal work do you want to practise?</p>
            <div className="space-y-3">
              {SCENARIOS.map((sc) => (
                <button
                  key={sc.id}
                  disabled={!sc.available}
                  onClick={() => {
                    setScenario(sc.id);
                    setStep("persona");
                  }}
                  className={`w-full text-left p-4 rounded-xl border transition-all ${
                    sc.available
                      ? scenario === sc.id
                        ? "border-indigo-500 bg-indigo-900/30"
                        : "border-gray-700 hover:border-gray-500 bg-gray-900"
                      : "border-gray-800 bg-gray-900/50 opacity-40 cursor-not-allowed"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{sc.label}</span>
                    {!sc.available && (
                      <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">Coming soon</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{sc.description}</p>
                </button>
              ))}
            </div>
          </>
        )}

        {step === "persona" && (
          <>
            <h1 className="text-2xl font-bold mb-2">Choose your opponent</h1>
            <p className="text-gray-400 text-sm mb-6">
              Persona changes style, not whether they resist. The ladder holds regardless.
            </p>
            <div className="space-y-3">
              {PERSONAS.map((p) => (
                <button
                  key={p.id}
                  disabled={!p.available}
                  onClick={() => {
                    setPersona(p.id);
                    setStep("confirm");
                  }}
                  className={`w-full text-left p-4 rounded-xl border transition-all ${
                    p.available
                      ? persona === p.id
                        ? "border-indigo-500 bg-indigo-900/30"
                        : "border-gray-700 hover:border-gray-500 bg-gray-900"
                      : "border-gray-800 bg-gray-900/50 opacity-40 cursor-not-allowed"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{p.label}</span>
                    {!p.available && (
                      <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">Coming soon</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{p.description}</p>
                </button>
              ))}
            </div>
            <button
              className="mt-6 text-sm text-gray-500 hover:text-gray-300"
              onClick={() => setStep("scenario")}
            >
              Back
            </button>
          </>
        )}

        {step === "confirm" && (
          <>
            <h1 className="text-2xl font-bold mb-2">Ready to begin</h1>
            <p className="text-gray-400 text-sm mb-8">
              You're about to negotiate a GDPR DPA against{" "}
              <span className="text-white font-medium">
                {PERSONAS.find((p) => p.id === persona)?.label}
              </span>
              .
            </p>

            <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6 space-y-3 text-sm">
              <div>
                <span className="text-gray-500">Scenario</span>
                <span className="ml-3 text-white">{SCENARIOS.find((s) => s.id === scenario)?.label}</span>
              </div>
              <div>
                <span className="text-gray-500">Opponent</span>
                <span className="ml-3 text-white">{PERSONAS.find((p) => p.id === persona)?.label}</span>
              </div>
              <div>
                <span className="text-gray-500">Mode</span>
                <span className="ml-3 text-white">Playbook</span>
              </div>
            </div>

            <div className="bg-amber-950/40 border border-amber-800/50 rounded-xl p-4 mb-8 text-sm text-amber-200">
              <strong>Briefing:</strong> You represent FinTech Corp (Controller) negotiating a Data Processing
              Agreement with CloudStack Ltd (Processor) for EU payroll data. Your partner made this DPA your
              personal responsibility after a prior ICO fine. The opponent will not fold to confidence — earn
              every concession on the legal merits.
            </div>

            <div className="flex gap-3">
              <button
                className="flex-1 px-4 py-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 font-semibold"
                onClick={() => onStart(scenario, persona, null)}
              >
                Enter the arena
              </button>
              <button
                className="px-4 py-3 text-gray-400 hover:text-gray-200"
                onClick={() => setStep("persona")}
              >
                Back
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
