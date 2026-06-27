import { difficulties, optionLabel, personas } from "./options";
import type { RoundState, VoiceDifficulty, VoicePersona } from "@/lib/voiceBackend";

type SessionHeaderProps = {
  difficulty: VoiceDifficulty;
  onBackToSetup: () => void;
  persona: VoicePersona;
  round: RoundState;
};

export function SessionHeader({ difficulty, onBackToSetup, persona, round }: SessionHeaderProps) {
  return (
    <header className="chat-header">
      <div>
        <p className="product-mark">Crucible</p>
        <h1>Voice sparring</h1>
      </div>
      <div className="session-meta" aria-label="Session status">
        <span>{optionLabel(personas, persona)}</span>
        <span>{optionLabel(difficulties, difficulty)}</span>
        <span>Turn {round.turn}</span>
        <span>{round.runtime}</span>
      </div>
      <button className="secondary-button compact" onClick={onBackToSetup} type="button">
        Setup
      </button>
    </header>
  );
}
