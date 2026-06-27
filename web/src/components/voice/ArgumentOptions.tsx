import type { ArgumentOption, ArgumentOptionsPayload } from "@/lib/voiceBackend";

type ArgumentOptionsProps = {
  error: string;
  grounding: Omit<ArgumentOptionsPayload, "options"> | null;
  loading: boolean;
  onRefresh: () => void;
  onSelect: (move: string) => void;
  options: ArgumentOption[];
};

export function ArgumentOptions({ error, grounding, loading, onRefresh, onSelect, options }: ArgumentOptionsProps) {
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
      {grounding ? <GroundingSummary grounding={grounding} /> : null}
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

function GroundingSummary({ grounding }: { grounding: Omit<ArgumentOptionsPayload, "options"> }) {
  const sources = grounding.sources.slice(0, 3);
  return (
    <div className="grounding-summary">
      <p>{grounding.grounding_note}</p>
      {grounding.tools_used.length ? (
        <div className="grounding-tools">
          {grounding.tools_used.map((tool) => <span key={tool}>{tool}</span>)}
        </div>
      ) : null}
      {sources.length ? (
        <ul className="grounding-sources">
          {sources.map((source) => (
            <li key={`${source.title}-${source.url ?? ""}`}>
              {source.url ? (
                <a href={source.url} rel="noreferrer" target="_blank">{source.title}</a>
              ) : (
                <span>{source.title}</span>
              )}
              {source.snippet ? <small>{source.snippet}</small> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
