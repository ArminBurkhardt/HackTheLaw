import { useState } from "react";
import RadarChart from "./RadarChart";
import ScenarioBriefStep from "./ScenarioBriefStep";
import { HARDNESS_LEVELS, PERSONAS, SCENARIOS, SCENARIO_BRIEFS } from "./scenarioPickerData";

interface Props {
  language: "en" | "de";
  onSettings: () => void;
  onViewProgress: () => void;
  onPrepare: (scenario: string, persona: string, hardness: string) => void;
  onStart: (scenario: string, persona: string, hardness: string, scoreToBeat: number | null) => void;
}

type Step = "scenario" | "persona" | "hardness" | "confirm" | "brief";

export default function ScenarioPicker({ language, onSettings, onViewProgress, onPrepare, onStart }: Props) {
  const [step, setStep] = useState<Step>("scenario");
  const [scenario, setScenario] = useState("negotiation");
  const [persona, setPersona] = useState("aggressor");
  const [hardness, setHardness] = useState("standard");

  const selectedPersona = PERSONAS.find((p) => p.id === persona)!;
  const selectedHardness = HARDNESS_LEVELS.find((h) => h.id === hardness)!;
  const brief = SCENARIO_BRIEFS[scenario];

  const steps: Step[] = ["scenario", "persona", "hardness", "confirm", "brief"];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-2xl">
        <div className="mb-6 flex items-center justify-between">
          <div className="text-xs uppercase tracking-widest text-gray-500">
            Language: {language === "de" ? "Deutsch" : "English"}
          </div>
          <div className="flex gap-3 text-sm">
            <button className="text-gray-400 hover:text-gray-200" onClick={onViewProgress}>
              Profile
            </button>
            <button className="text-gray-400 hover:text-gray-200" onClick={onSettings}>
              Settings
            </button>
          </div>
        </div>

        {/* Progress pills */}
        <div className="flex gap-2 mb-10">
          {steps.map((s, i) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors ${
                step === s
                  ? "bg-indigo-500"
                  : i < steps.indexOf(step)
                  ? "bg-indigo-800"
                  : "bg-gray-700"
              }`}
            />
          ))}
        </div>

        {/* ── Step 1: Scenario ───────────────────────────────────────── */}
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
                      <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                        Coming soon
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{sc.description}</p>
                </button>
              ))}
            </div>
          </>
        )}

        {/* ── Step 2: Persona ─────────────────────────────────────────── */}
        {step === "persona" && (
          <>
            <h1 className="text-2xl font-bold mb-2">Choose your opponent</h1>
            <p className="text-gray-400 text-sm mb-6">
              Persona changes style, not whether they resist. The ladder holds regardless.
            </p>
            <div className="space-y-3">
              {PERSONAS.map((p) => {
                const selected = persona === p.id;
                return (
                  <button
                    key={p.id}
                    disabled={!p.available}
                    onClick={() => {
                      setPersona(p.id);
                      setStep("hardness");
                    }}
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      p.available
                        ? selected
                          ? "border-indigo-500 bg-indigo-900/30"
                          : "border-gray-700 hover:border-gray-500 bg-gray-900"
                        : "border-gray-800 bg-gray-900/50 opacity-40 cursor-not-allowed"
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold">{p.label}</span>
                          {!p.available && (
                            <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                              Coming soon
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-400 mt-1">{p.description}</p>
                        {p.available && (
                          <p className="text-xs text-indigo-400 mt-2 italic">{p.tagline}</p>
                        )}
                      </div>
                      {/* Mini radar preview for available personas */}
                      {p.available && (
                        <div className="shrink-0 opacity-80">
                          <RadarChart
                            axes={p.radar}
                            max={1}
                            size={80}
                            color="#6366f1"
                            fillOpacity={0.3}
                          />
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
            <button
              className="mt-6 text-sm text-gray-500 hover:text-gray-300"
              onClick={() => setStep("scenario")}
            >
              ← Back
            </button>
          </>
        )}

        {/* ── Step 3: Hardness ─────────────────────────────────────────── */}
        {step === "hardness" && (
          <>
            <h1 className="text-2xl font-bold mb-2">Choose hardness</h1>
            <p className="text-gray-400 text-sm mb-6">
              Same SaaS playbook, different resistance level. Hardness changes concession strictness, not the case.
            </p>
            <div className="space-y-3">
              {HARDNESS_LEVELS.map((level) => {
                const selected = hardness === level.id;
                return (
                  <button
                    key={level.id}
                    onClick={() => {
                      setHardness(level.id);
                      setStep("confirm");
                    }}
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      selected ? "border-indigo-500 bg-indigo-900/30" : "border-gray-700 hover:border-gray-500 bg-gray-900"
                    }`}
                  >
                    <div className="font-semibold">{level.label}</div>
                    <p className="text-sm text-gray-400 mt-1">{level.description}</p>
                    <p className="text-xs text-indigo-400 mt-2">{level.effect}</p>
                  </button>
                );
              })}
            </div>
            <button
              className="mt-6 text-sm text-gray-500 hover:text-gray-300"
              onClick={() => setStep("persona")}
            >
              ← Back
            </button>
          </>
        )}

        {/* ── Step 4: Confirm + large persona radar ───────────────────── */}
        {step === "confirm" && (
          <>
            <h1 className="text-2xl font-bold mb-2">Your opponent</h1>
            <p className="text-gray-400 text-sm mb-6">
              Study the profile. This is what you're walking into.
            </p>

            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 mb-6 flex gap-6 items-center">
              {/* Radar */}
              <div className="shrink-0">
                <RadarChart
                  axes={selectedPersona.radar}
                  max={1}
                  size={160}
                  color="#6366f1"
                  fillOpacity={0.3}
                />
              </div>
              {/* Info */}
              <div className="flex-1">
                <div className="text-lg font-bold mb-1">{selectedPersona.label}</div>
                <p className="text-sm text-gray-300 mb-3">{selectedPersona.description}</p>
                <p className="text-xs text-indigo-400 italic mb-4">{selectedPersona.tagline}</p>
                <div className="space-y-1.5">
                  {selectedPersona.radar.map((ax) => (
                    <div key={ax.label} className="flex items-center gap-2">
                      <span className="text-xs text-gray-500 w-20">{ax.label}</span>
                      <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full"
                          style={{ width: `${ax.value * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-6 text-right">
                        {Math.round(ax.value * 10)}/10
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-6 space-y-2 text-sm">
              <div>
                <span className="text-gray-500">Scenario</span>
                <span className="ml-3 text-white">
                  {SCENARIOS.find((s) => s.id === scenario)?.label}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Mode</span>
                <span className="ml-3 text-white">Playbook</span>
              </div>
              <div>
                <span className="text-gray-500">Hardness</span>
                <span className="ml-3 text-white">{selectedHardness.label}</span>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                className="flex-1 px-4 py-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 font-semibold"
                onClick={() => {
                  setStep("brief");
                  onPrepare(scenario, persona, hardness);
                }}
              >
                Continue to briefing →
              </button>
              <button
                className="px-4 py-3 text-gray-400 hover:text-gray-200"
                onClick={() => setStep("hardness")}
              >
                Back
              </button>
            </div>
          </>
        )}

        {/* ── Step 5: Pre-session brief ────────────────────────────────── */}
        {step === "brief" && brief && (
          <ScenarioBriefStep
            brief={brief}
            onBack={() => setStep("confirm")}
            onStart={() => onStart(scenario, persona, hardness, null)}
          />
        )}
      </div>
    </div>
  );
}
