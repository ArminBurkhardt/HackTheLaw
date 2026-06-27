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
        <button className="secondary-button compact" onClick={onReplay} type="button">
          Replay
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
