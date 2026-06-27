import { useRef, useState } from "react";
import { generateScenarioFromPlaybook } from "./lib/ws";
import type { GeneratedScenario } from "./lib/ws";

interface Props {
  language: "en" | "de";
  onGenerated: (scenario: GeneratedScenario) => void;
}

export default function ScenarioUpload({ language, onGenerated }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createScenario() {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    try {
      const scenario = await generateScenarioFromPlaybook(file, language);
      onGenerated(scenario);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="scenario-upload-panel mb-6 rounded-xl border border-gray-800 bg-gray-900/70 p-4">
      <div className="mb-3">
        <div className="text-sm font-semibold text-gray-100">Create from playbook</div>
        <p className="mt-1 text-xs text-gray-500">
          Upload a PDF, TXT, or Markdown playbook and generate an arena scenario.
        </p>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          ref={inputRef}
          className="hidden"
          type="file"
          accept=".pdf,.txt,.md,.markdown,application/pdf,text/plain,text/markdown"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setError(null);
          }}
        />
        <button
          className="scenario-upload-secondary rounded-lg border border-gray-700 px-4 py-2 text-left text-sm text-gray-300 hover:border-gray-500"
          onClick={() => inputRef.current?.click()}
          type="button"
        >
          {file ? file.name : "Choose playbook"}
        </button>
        <button
          className="scenario-upload-primary rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!file || busy}
          onClick={createScenario}
          type="button"
        >
          {busy ? "Creating..." : "Create scenario"}
        </button>
      </div>
      {error && <div className="mt-3 rounded-lg bg-rose-950 px-3 py-2 text-xs text-rose-100">{error}</div>}
    </div>
  );
}
