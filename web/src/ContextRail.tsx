import { RoundContext } from "./lib/ws";
import { MOVE_ICON, MOVE_COLOR, classificationLabel } from "./arena/labels";

interface Props {
  context: RoundContext | null;
  error: string | null;
  loading: boolean;
  onRefresh: () => void;
}

const TOOL_LABELS: Record<string, string> = {
  perplexity_search: "Perplexity",
  neo4j_cellar: "CELLAR",
};

export default function ContextRail({ context, error, loading, onRefresh }: Props) {
  return (
    <aside className="xl:w-80 lg:w-72 w-full bg-gray-900 border border-gray-800 rounded-2xl p-4 space-y-4 h-fit">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold tracking-tight">Live context</h2>
          <p className="text-xs text-gray-500">Grounding, tools, and playbook hooks</p>
        </div>
        <button
          className="text-xs text-gray-400 hover:text-gray-200 disabled:opacity-40"
          disabled={loading}
          onClick={onRefresh}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800/50 bg-rose-950/30 p-3 text-xs text-rose-200">
          {error}
        </div>
      )}

      <section>
        <h3 className="text-xs uppercase tracking-widest text-gray-500 mb-2">Tools</h3>
        <div className="flex flex-wrap gap-2">
          {(context?.tools ?? []).map((tool) => (
            <span
              key={tool.name}
              title={tool.detail}
              className={`text-xs rounded-full border px-2 py-1 ${
                tool.status === "ok"
                  ? "border-emerald-700/60 bg-emerald-950/30 text-emerald-300"
                  : tool.status === "error"
                  ? "border-rose-800/60 bg-rose-950/30 text-rose-300"
                  : "border-gray-700 bg-gray-950 text-gray-500"
              }`}
            >
              {TOOL_LABELS[tool.name] ?? tool.name}
            </span>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-xs uppercase tracking-widest text-gray-500 mb-2">Argument hooks</h3>
        <div className="space-y-2">
          {(context?.hooks ?? []).slice(0, 3).map((hook) => (
            <article key={hook.id} className="rounded-lg bg-gray-950 border border-gray-800 p-3">
              <div className="text-sm text-gray-200 font-medium">{hook.label}</div>
              <p className="mt-1 text-xs text-gray-500 leading-relaxed">{hook.target}</p>
              {hook.authorities.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {hook.authorities.map((authority) => (
                    <span
                      key={`${authority.title}-${authority.pinpoint ?? ""}`}
                      className="rounded bg-indigo-950/60 border border-indigo-800/50 px-1.5 py-0.5 text-[11px] text-indigo-300"
                    >
                      {authority.pinpoint ?? authority.title}
                    </span>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </section>

      {context?.last_move && (
        <section>
          <h3 className="text-xs uppercase tracking-widest text-gray-500 mb-2">Last adjudication</h3>
          <div className="rounded-lg border border-gray-800 bg-gray-950 p-3 text-xs text-gray-300 flex gap-2.5">
            <img
              src={MOVE_ICON[context.last_move.classification]}
              alt={classificationLabel(context.last_move.classification)}
              className="w-5 h-5 shrink-0 mt-0.5"
            />
            <div className="min-w-0">
              <div className={`font-semibold ${MOVE_COLOR[context.last_move.classification]}`}>
                {classificationLabel(context.last_move.classification)}
              </div>
              <p className="mt-1 leading-relaxed text-gray-500">{context.last_move.note}</p>
            </div>
          </div>
        </section>
      )}

      <section>
        <h3 className="text-xs uppercase tracking-widest text-gray-500 mb-2">Sources</h3>
        <div className="space-y-2">
          {(context?.sources ?? []).length === 0 ? (
            <p className="text-xs text-gray-600">No live grounding sources returned yet.</p>
          ) : (
            context?.sources.slice(0, 4).map((source) => (
              <article key={`${source.tool}-${source.title}-${source.pinpoint ?? ""}`} className="text-xs">
                <div className="text-gray-300">
                  {source.url ? (
                    <a className="hover:text-indigo-300" href={source.url} rel="noreferrer" target="_blank">
                      {source.title}
                    </a>
                  ) : (
                    source.title
                  )}
                  {source.pinpoint ? <span className="text-gray-500"> · {source.pinpoint}</span> : null}
                </div>
                {source.snippet ? <p className="mt-0.5 line-clamp-2 text-gray-600">{source.snippet}</p> : null}
              </article>
            ))
          )}
        </div>
      </section>
    </aside>
  );
}
