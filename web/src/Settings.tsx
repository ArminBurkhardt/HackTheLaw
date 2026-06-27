export type AppLanguage = "en" | "de";

interface Props {
  language: AppLanguage;
  onLanguageChange: (language: AppLanguage) => void;
  onViewProgress: () => void;
  onBack: () => void;
}

const LANGUAGES: Array<{ id: AppLanguage; label: string; detail: string }> = [
  { id: "en", label: "English", detail: "Opponent replies and Gemini Live audio in English." },
  { id: "de", label: "Deutsch", detail: "Opponent replies and Gemini Live audio in German." },
];

export default function Settings({ language, onLanguageChange, onViewProgress, onBack }: Props) {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="mx-auto max-w-xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
          <button onClick={onBack} className="text-sm text-gray-400 hover:text-gray-200">
            Back
          </button>
        </div>

        <section className="mb-5 rounded-xl border border-gray-800 bg-gray-900 p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-widest text-gray-500">
            Session language
          </h2>
          <div className="space-y-3">
            {LANGUAGES.map((option) => (
              <button
                key={option.id}
                onClick={() => onLanguageChange(option.id)}
                className={`w-full rounded-lg border p-4 text-left transition ${
                  language === option.id
                    ? "border-indigo-500 bg-indigo-950/40"
                    : "border-gray-800 bg-gray-950 hover:border-gray-600"
                }`}
              >
                <div className="font-medium text-gray-100">{option.label}</div>
                <div className="mt-1 text-sm text-gray-500">{option.detail}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-gray-800 bg-gray-900 p-5">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-widest text-gray-500">
            Profile
          </h2>
          <p className="mb-4 text-sm text-gray-400">
            Review scores, streaks, persona mastery, and recurring weaknesses from completed rounds.
          </p>
          <button
            onClick={onViewProgress}
            className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-950 hover:bg-white"
          >
            Open profile overview
          </button>
        </section>
      </div>
    </div>
  );
}
