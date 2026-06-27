import type { ScenarioBrief } from "./scenarioPickerData";

interface Props {
  brief: ScenarioBrief;
  onBack: () => void;
  onStart: () => void;
}

export default function ScenarioBriefStep({ brief, onBack, onStart }: Props) {
  return (
    <>
      <h1 className="text-2xl font-bold mb-1">Pre-session briefing</h1>
      <p className="text-gray-400 text-sm mb-6">
        Know your strategy. The opponent will not wait.
      </p>

      <div className="bg-emerald-950/20 border border-emerald-800/30 rounded-xl p-5 mb-4">
        <div className="text-xs text-emerald-400 font-semibold uppercase tracking-widest mb-3">
          Strategy
        </div>
        <ul className="space-y-2">
          {brief.strategy.map((tip, index) => (
            <li key={index} className="flex gap-2 text-sm text-emerald-100">
              <span className="text-emerald-500 shrink-0">✓</span>
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-amber-950/20 border border-amber-800/30 rounded-xl p-5 mb-8">
        <div className="text-xs text-amber-400 font-semibold uppercase tracking-widest mb-3">
          Watch out for
        </div>
        <ul className="space-y-2">
          {brief.watchOut.map((item, index) => (
            <li key={index} className="flex gap-2 text-sm text-amber-100">
              <span className="text-amber-500 shrink-0">⚠</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex gap-3">
        <button
          className="flex-1 px-4 py-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 font-semibold text-base"
          onClick={onStart}
        >
          Enter the arena
        </button>
        <button
          className="px-4 py-3 text-gray-400 hover:text-gray-200"
          onClick={onBack}
        >
          Back
        </button>
      </div>
    </>
  );
}
