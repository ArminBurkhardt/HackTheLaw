import ScenarioUpload from "./ScenarioUpload";
import type { ScenarioDef } from "./scenarioPickerData";
import type { GeneratedScenario } from "./lib/ws";

interface Props {
  language: "en" | "de";
  scenarios: ScenarioDef[];
  selectedScenario: string;
  onChoose: (scenario: string) => void;
  onGenerated: (scenario: GeneratedScenario) => void;
}

export default function ScenarioChoiceStep({
  language,
  scenarios,
  selectedScenario,
  onChoose,
  onGenerated,
}: Props) {
  return (
    <>
      <h1 className="text-2xl font-bold mb-2">Choose your scenario</h1>
      <p className="text-gray-400 text-sm mb-6">What kind of legal work do you want to practise?</p>
      <ScenarioUpload language={language} onGenerated={onGenerated} />
      <div className="space-y-3">
        {scenarios.map((sc) => (
          <button
            key={sc.id}
            disabled={!sc.available}
            onClick={() => onChoose(sc.id)}
            className={`w-full text-left p-4 rounded-xl border transition-all ${
              sc.available
                ? selectedScenario === sc.id
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
  );
}
