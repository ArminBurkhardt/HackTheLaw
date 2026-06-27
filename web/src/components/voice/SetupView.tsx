import { difficulties, personas } from "./options";
import type { VoiceDifficulty, VoicePersona } from "@/lib/voiceBackend";

type SetupViewProps = {
  busy: boolean;
  difficulty: VoiceDifficulty;
  error: string;
  onDifficultyChange: (difficulty: VoiceDifficulty) => void;
  onPersonaChange: (persona: VoicePersona) => void;
  onStart: () => void;
  persona: VoicePersona;
  voiceAvailable: boolean;
};

export function SetupView({
  busy,
  difficulty,
  error,
  onDifficultyChange,
  onPersonaChange,
  onStart,
  persona,
  voiceAvailable,
}: SetupViewProps) {
  return (
    <main className="setup-shell">
      <section className="setup-card">
        <div className="setup-copy">
          <p className="product-mark">Crucible</p>
          <h1>Set up your sparring session</h1>
          <p>
            Choose the conversation persona and course level first. The next screen is a focused chat surface
            with the input pinned to the bottom.
          </p>
          <div className="setup-status">
            <span>{voiceAvailable ? "Microphone available" : "Text mode available"}</span>
            <span>Credential-backed backend required</span>
          </div>
        </div>

        <div className="setup-grid">
          <section className="setup-section">
            <h2>Persona</h2>
            <div className="option-list">
              {personas.map((item) => (
                <button
                  className={item.id === persona ? "option-card active" : "option-card"}
                  key={item.id}
                  onClick={() => onPersonaChange(item.id)}
                  type="button"
                >
                  <span>{item.label}</span>
                  <small>{item.detail}</small>
                </button>
              ))}
            </div>
          </section>

          <section className="setup-section">
            <h2>Course level</h2>
            <div className="option-list">
              {difficulties.map((item) => (
                <button
                  className={item.id === difficulty ? "option-card active" : "option-card"}
                  key={item.id}
                  onClick={() => onDifficultyChange(item.id)}
                  type="button"
                >
                  <span>{item.label}</span>
                  <small>{item.detail}</small>
                </button>
              ))}
            </div>
          </section>
        </div>

        {error ? <p className="setup-error">{error}</p> : null}
        <button className="primary-button setup-start" disabled={busy} onClick={onStart} type="button">
          {busy ? "Connecting..." : "Start session"}
        </button>
      </section>
    </main>
  );
}
