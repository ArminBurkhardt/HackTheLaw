import { ArgumentOptions } from "./ArgumentOptions";
import { difficulties, optionLabel, personas } from "./options";
import type { ArgumentOption, RoundState, VoiceDifficulty, VoicePersona } from "@/lib/voiceBackend";

type SessionContextProps = {
  argumentOptions: ArgumentOption[];
  argumentOptionsError: string;
  argumentOptionsLoading: boolean;
  difficulty: VoiceDifficulty;
  onRefreshArgumentOptions: () => void;
  onSelectArgument: (move: string) => void;
  persona: VoicePersona;
  round: RoundState;
};

export function SessionContext({
  argumentOptions,
  argumentOptionsError,
  argumentOptionsLoading,
  difficulty,
  onRefreshArgumentOptions,
  onSelectArgument,
  persona,
  round,
}: SessionContextProps) {
  const latestOpponent = round.messages.filter((message) => message.role === "opponent").at(-1)?.text;

  return (
    <aside className="context-rail" aria-label="Session context">
      <section className="context-section">
        <h2>Task context</h2>
        <p>
          Negotiate DPA audit and processor-control language without conceding leverage too early.
        </p>
      </section>

      <section className="context-section">
        <h2>Session</h2>
        <dl className="context-list">
          <div><dt>Persona</dt><dd>{optionLabel(personas, persona)}</dd></div>
          <div><dt>Course level</dt><dd>{optionLabel(difficulties, difficulty)}</dd></div>
          <div><dt>Runtime</dt><dd>{round.runtime}</dd></div>
        </dl>
      </section>

      <section className="context-section">
        <h2>Relevant hooks</h2>
        <ul className="context-bullets">
          <li>Anchor changes in GDPR Art. 28 processor obligations.</li>
          <li>Tie audit rights to cadence, triggers, and evidence access.</li>
          <li>Trade movement for reciprocal confidentiality or liability terms.</li>
        </ul>
      </section>

      <ArgumentOptions
        error={argumentOptionsError}
        loading={argumentOptionsLoading}
        onRefresh={onRefreshArgumentOptions}
        onSelect={onSelectArgument}
        options={argumentOptions}
      />

      {latestOpponent ? (
        <section className="context-section">
          <h2>Opponent position</h2>
          <p>{latestOpponent}</p>
        </section>
      ) : null}
    </aside>
  );
}
