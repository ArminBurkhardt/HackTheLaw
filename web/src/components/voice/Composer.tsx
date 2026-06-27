import type { FormEvent } from "react";

type ComposerProps = {
  busy: boolean;
  draft: string;
  listening: boolean;
  onDraftChange: (draft: string) => void;
  onFinish: () => void;
  onReplay: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggleListening: () => void;
  speaking: boolean;
  speechAvailable: boolean;
  voiceAvailable: boolean;
};

export function Composer({
  busy,
  draft,
  listening,
  onDraftChange,
  onFinish,
  onReplay,
  onSubmit,
  onToggleListening,
  speaking,
  speechAvailable,
  voiceAvailable,
}: ComposerProps) {
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
        <span className={speaking ? "voice-state active" : "voice-state"}>
          {speechAvailable ? (speaking ? "Gemini Live speaking" : "Gemini Live audio") : "Audio unavailable"}
        </span>
        <button className="secondary-button compact" disabled={!speechAvailable} onClick={onReplay} type="button">
          Speak again
        </button>
        <button className="secondary-button compact" disabled={busy} onClick={onFinish} type="button">
          End
        </button>
        <button
          className={listening ? "danger-button compact" : "secondary-button compact"}
          disabled={!voiceAvailable || busy}
          onClick={onToggleListening}
          type="button"
        >
          {listening ? "Stop" : "Mic"}
        </button>
        <button className="primary-button compact" disabled={busy || !draft.trim()} type="submit">
          Send
        </button>
      </div>
    </form>
  );
}
