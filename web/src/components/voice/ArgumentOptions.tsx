import type { ArgumentOption } from "@/lib/voiceBackend";

type ArgumentOptionsProps = {
  error: string;
  loading: boolean;
  onRefresh: () => void;
  onSelect: (move: string) => void;
  options: ArgumentOption[];
};

export function ArgumentOptions({ error, loading, onRefresh, onSelect, options }: ArgumentOptionsProps) {
  return (
    <section className="context-section">
      <div className="context-title-row">
        <h2>Generated options</h2>
        <button className="secondary-button compact" disabled={loading} onClick={onRefresh} type="button">
          Refresh
        </button>
      </div>
      {loading ? <p className="context-muted">Generating argument cards from the current transcript...</p> : null}
      {error ? <p className="context-error">{error}</p> : null}
      <div className="argument-options">
        {options.map((option) => (
          <article className="argument-option" key={`${option.label}-${option.move}`}>
            <strong>{option.label}</strong>
            <p>{option.rationale}</p>
            <button className="secondary-button compact" onClick={() => onSelect(option.move)} type="button">
              Use as draft
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
