import type { FormEvent } from "react";
import { Mic, MicOff, SendHorizontal, Square, Volume2 } from "lucide-react";

type ComposerProps = {
  audioStatus: "idle" | "preparing" | "speaking";
  busy: boolean;
  draft: string;
  listening: boolean;
  onDraftChange: (draft: string) => void;
  onFinish: () => void;
  onReplay: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggleListening: () => void;
  speechAvailable: boolean;
  voiceAvailable: boolean;
};

export function Composer({
  audioStatus,
  busy,
  draft,
  listening,
  onDraftChange,
  onFinish,
  onReplay,
  onSubmit,
  onToggleListening,
  speechAvailable,
  voiceAvailable,
}: ComposerProps) {
  const audioLabel = audioStatus === "preparing"
    ? "Preparing Gemini Live audio"
    : audioStatus === "speaking"
      ? "Gemini Live speaking"
      : "Gemini Live audio";

  return (
    <form className="composer" onSubmit={onSubmit}>
      <textarea
        className="composer-input"
        onChange={(event) => onDraftChange(event.target.value)}
        placeholder="Message your sparring partner..."
        rows={1}
        value={draft}
      />
      <div className="composer-actions">
        <span className={audioStatus === "idle" ? "voice-state" : "voice-state active"}>
          {speechAvailable ? audioLabel : "Audio unavailable"}
        </span>
        <button
          aria-label="Speak again"
          className="secondary-button compact icon-button"
          disabled={!speechAvailable}
          onClick={onReplay}
          title="Speak again"
          type="button"
        >
          <Volume2 aria-hidden="true" size={17} />
        </button>
        <button
          aria-label="End session"
          className="secondary-button compact icon-button"
          disabled={busy}
          onClick={onFinish}
          title="End session"
          type="button"
        >
          <Square aria-hidden="true" size={16} />
        </button>
        <button
          aria-label={listening ? "Stop microphone" : "Start microphone"}
          className={listening ? "danger-button compact icon-button" : "secondary-button compact icon-button"}
          disabled={!voiceAvailable || busy}
          onClick={onToggleListening}
          title={listening ? "Stop microphone" : "Start microphone"}
          type="button"
        >
          {listening ? <MicOff aria-hidden="true" size={17} /> : <Mic aria-hidden="true" size={17} />}
        </button>
        <button
          aria-label="Send message"
          className="primary-button compact icon-button"
          disabled={busy || !draft.trim()}
          title="Send message"
          type="submit"
        >
          <SendHorizontal aria-hidden="true" size={17} />
        </button>
      </div>
    </form>
  );
}
