import { Settings } from "lucide-react";

import { difficulties, languages, optionLabel, personas } from "./options";
import type { RoundState, VoiceDifficulty, VoiceLanguage, VoicePersona } from "@/lib/voiceBackend";

type SessionHeaderProps = {
  difficulty: VoiceDifficulty;
  language: VoiceLanguage;
  onBackToSetup: () => void;
  persona: VoicePersona;
  round: RoundState;
};

export function SessionHeader({ difficulty, language, onBackToSetup, persona, round }: SessionHeaderProps) {
  return (
    <header className="chat-header">
      <div>
        <p className="product-mark">Crucible</p>
        <h1>Voice sparring</h1>
      </div>
      <div className="session-meta" aria-label="Session status">
        <span>{optionLabel(personas, persona)}</span>
        <span>{optionLabel(difficulties, difficulty)}</span>
        <span>{optionLabel(languages, language)}</span>
        <span>Turn {round.turn}</span>
        <span>{round.runtime}</span>
      </div>
      <button
        aria-label="Open session setup"
        className="secondary-button compact icon-button"
        onClick={onBackToSetup}
        title="Open session setup"
        type="button"
      >
        <Settings aria-hidden="true" size={17} />
      </button>
    </header>
  );
}
