import { useState } from "react";
import RadarChart, { RadarAxis } from "./RadarChart";

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

interface PersonaDef {
  id: string;
  label: string;
  description: string;
  available: boolean;
  radar: RadarAxis[];
  tagline: string;
}

const PERSONAS: PersonaDef[] = [
  {
    id: "aggressor",
    label: "The Aggressor",
    description: "Deadline-obsessed, ultimatum-prone, exploits every hesitation.",
    tagline: "High pressure. Zero patience. Every pause is a weakness.",
    available: true,
    radar: [
      { label: "Aggression", value: 0.9 },
      { label: "Pressure", value: 0.9 },
      { label: "Verbosity", value: 0.6 },
      { label: "Tempo", value: 0.8 },
      { label: "Flexibility", value: 0.2 },
    ],
  },
  {
    id: "charmer",
    label: "The Charmer",
    description: "Warm and collegial — dangerous because you lower your guard.",
    tagline: "Friendly fire. False consensus. The compliment is the trap.",
    available: false,
    radar: [
      { label: "Aggression", value: 0.3 },
      { label: "Pressure", value: 0.4 },
      { label: "Verbosity", value: 0.8 },
      { label: "Tempo", value: 0.5 },
      { label: "Flexibility", value: 0.5 },
    ],
  },
  {
    id: "stonewaller",
    label: "The Stonewaller",
    description: "Monosyllabic and immovable. Waits you out.",
    tagline: "Silence is strategy. They will outlast you.",
    available: false,
    radar: [
      { label: "Aggression", value: 0.5 },
      { label: "Pressure", value: 0.6 },
      { label: "Verbosity", value: 0.3 },
      { label: "Tempo", value: 0.2 },
      { label: "Flexibility", value: 0.1 },
    ],
  },
  {
    id: "technician",
    label: "The Technician",
    description: "Buries you in clause numbers and recital references.",
    tagline: "Chapter-and-verse arguments only. Vague citations crumble.",
    available: false,
    radar: [
      { label: "Aggression", value: 0.4 },
      { label: "Pressure", value: 0.5 },
      { label: "Verbosity", value: 0.9 },
      { label: "Tempo", value: 0.6 },
      { label: "Flexibility", value: 0.4 },
    ],
  },
];

interface BriefEntry {
  title: string;
  pinpoint: string;
  note: string;
}

const SCENARIO_BRIEFS: Record<string, {
  authorities: BriefEntry[];
  strategy: string[];
  watchOut: string[];
}> = {
  negotiation: {
    authorities: [
      { title: "GDPR Art. 28", pinpoint: "Art. 28", note: "Controller-Processor requirements — your primary anchor" },
      { title: "GDPR Art. 28(2)", pinpoint: "Art. 28(2)", note: "Written authorisation required before sub-processors are engaged" },
      { title: "GDPR Art. 28(3)(d)", pinpoint: "Art. 28(3)(d)", note: "Sub-processor must face identical obligations — cite (2) and (3)(d) together" },
      { title: "GDPR Art. 28(3)(h)", pinpoint: "Art. 28(3)(h)", note: "Audit rights — never soften these to unlock a commercial concession" },
      { title: "GDPR Art. 83(4)", pinpoint: "Art. 83(4)", note: "Fines up to €10M / 2% global turnover — quantify the shared exposure" },
    ],
    strategy: [
      "Cite Art. 28(2) and Art. 28(3)(d) together — prior authorisation plus flow-down obligations form a complete shield.",
      "Lock all must-haves before any concession. Art. 28(3)(h) audit rights are non-negotiable.",
      "Vague GDPR references satisfy no unlock condition. The opponent's ladder demands chapter-and-verse precision.",
      "Quantify shared exposure: Art. 83(4) fines are not just your problem — use that to reset their BATNA.",
    ],
    watchOut: [
      "Commercial pressure before data protection clauses are locked — resist this order inversion.",
      "'Reasonable endeavours' replacing specific GDPR obligations — reject every instance.",
      "The opponent's BATNA is real. Know when a win is a win rather than pushing for more.",
    ],
  },
};

type Step = "scenario" | "persona" | "confirm" | "brief";

export default function ScenarioPicker({ onStart }: Props) {
  const [step, setStep] = useState<Step>("scenario");
  const [scenario, setScenario] = useState("negotiation");
  const [persona, setPersona] = useState("aggressor");

  const selectedPersona = PERSONAS.find((p) => p.id === persona)!;
  const brief = SCENARIO_BRIEFS[scenario];

  const steps: Step[] = ["scenario", "persona", "confirm", "brief"];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-2xl">
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
                      setStep("confirm");
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

        {/* ── Step 3: Confirm + large persona radar ───────────────────── */}
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
            </div>

            <div className="flex gap-3">
              <button
                className="flex-1 px-4 py-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 font-semibold"
                onClick={() => setStep("brief")}
              >
                Continue to briefing →
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

        {/* ── Step 4: Pre-session brief ────────────────────────────────── */}
        {step === "brief" && brief && (
          <>
            <h1 className="text-2xl font-bold mb-1">Pre-session briefing</h1>
            <p className="text-gray-400 text-sm mb-6">
              Know your authorities. Know your strategy. The opponent will not wait.
            </p>

            {/* Key authorities */}
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-4">
              <div className="text-xs text-indigo-400 font-semibold uppercase tracking-widest mb-3">
                Key authorities
              </div>
              <div className="space-y-3">
                {brief.authorities.map((a, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="shrink-0 text-xs font-mono bg-indigo-900/50 border border-indigo-700/50 text-indigo-300 rounded px-2 py-0.5 self-start">
                      {a.pinpoint}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-gray-200">{a.title}</div>
                      <div className="text-xs text-gray-400 mt-0.5">{a.note}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Strategy */}
            <div className="bg-emerald-950/20 border border-emerald-800/30 rounded-xl p-5 mb-4">
              <div className="text-xs text-emerald-400 font-semibold uppercase tracking-widest mb-3">
                Strategy
              </div>
              <ul className="space-y-2">
                {brief.strategy.map((tip, i) => (
                  <li key={i} className="flex gap-2 text-sm text-emerald-100">
                    <span className="text-emerald-500 shrink-0">✓</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Watch out */}
            <div className="bg-amber-950/20 border border-amber-800/30 rounded-xl p-5 mb-8">
              <div className="text-xs text-amber-400 font-semibold uppercase tracking-widest mb-3">
                Watch out for
              </div>
              <ul className="space-y-2">
                {brief.watchOut.map((item, i) => (
                  <li key={i} className="flex gap-2 text-sm text-amber-100">
                    <span className="text-amber-500 shrink-0">⚠</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex gap-3">
              <button
                className="flex-1 px-4 py-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 font-semibold text-base"
                onClick={() => onStart(scenario, persona, null)}
              >
                Enter the arena
              </button>
              <button
                className="px-4 py-3 text-gray-400 hover:text-gray-200"
                onClick={() => setStep("confirm")}
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
