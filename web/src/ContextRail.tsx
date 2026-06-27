import type { ReactNode } from "react";
import { RoundContext } from "./lib/ws";
import { MOVE_ICON, MOVE_COLOR, classificationLabel } from "./arena/labels";

interface Props {
  context: RoundContext | null;
  error: string | null;
  loading: boolean;
  onRefresh: () => void;
  onClose?: () => void;
}

const TOOL_LABELS: Record<string, string> = {
  perplexity_search: "Perplexity",
  neo4j_cellar: "CELLAR",
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="text-[10px] uppercase tracking-[0.18em] text-gray-500 font-semibold mb-2.5 px-0.5">{title}</h3>
      {children}
    </section>
  );
}

export default function ContextRail({ context, error, loading, onRefresh, onClose }: Props) {
  const hooks = (context?.hooks ?? []).slice(0, 3);
  const sources = context?.sources ?? [];
  const lastMove = context?.last_move ?? null;

  return (
    <aside className="flex flex-col h-full bg-gray-900 border-l border-gray-800">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 h-[68px] px-5 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2.5">
          <span className="grid place-items-center w-8 h-8 rounded-xl bg-indigo-500/15 text-indigo-300">
            <RadarIcon />
          </span>
          <div>
            <h2 className="text-sm font-semibold tracking-tight leading-tight">Live context</h2>
            <p className="text-[11px] text-gray-500">Grounding & playbook</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            className="grid place-items-center w-8 h-8 rounded-lg text-gray-500 hover:text-gray-100 hover:bg-gray-800 disabled:opacity-40 transition-colors"
            disabled={loading}
            onClick={onRefresh}
            title="Refresh"
          >
            <RefreshIcon spinning={loading} />
          </button>
          {onClose && (
            <button
              className="lg:hidden grid place-items-center w-8 h-8 rounded-lg text-gray-500 hover:text-gray-100 hover:bg-gray-800"
              onClick={onClose}
              title="Close"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 min-h-0 overflow-y-auto px-5 py-5 space-y-7">
        {error && (
          <div className="rounded-xl border border-rose-800/50 bg-rose-950/30 p-3 text-xs text-rose-200">{error}</div>
        )}

        {/* Last move — hero feedback card */}
        {lastMove && (
          <Section title="Last move">
            <div className="relative overflow-hidden rounded-2xl border border-gray-700 bg-gray-800 p-4">
              <div className="flex items-start gap-3">
                <img
                  src={MOVE_ICON[lastMove.classification]}
                  alt={classificationLabel(lastMove.classification)}
                  className="w-9 h-9 shrink-0"
                />
                <div className="min-w-0">
                  <div className={`text-sm font-bold capitalize ${MOVE_COLOR[lastMove.classification]}`}>
                    {classificationLabel(lastMove.classification)}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-gray-400">{lastMove.note}</p>
                </div>
              </div>
            </div>
          </Section>
        )}

        {/* Argument hooks */}
        <Section title="Argument hooks">
          {hooks.length === 0 ? (
            <p className="text-xs text-gray-600">No hooks surfaced yet.</p>
          ) : (
            <div className="space-y-2">
              {hooks.map((hook) => (
                <article
                  key={hook.id}
                  className="group rounded-2xl border border-gray-800 bg-gray-950 p-3.5 hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-start gap-2">
                    <span className="mt-1 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                    <div className="min-w-0">
                      <div className="text-sm text-gray-100 font-medium leading-snug">{hook.label}</div>
                      <p className="mt-1 text-xs text-gray-500 leading-relaxed">{hook.target}</p>
                    </div>
                  </div>
                  {hook.authorities.length > 0 && (
                    <div className="mt-2.5 flex flex-wrap gap-1.5 pl-3.5">
                      {hook.authorities.map((authority) => (
                        <span
                          key={`${authority.title}-${authority.pinpoint ?? ""}`}
                          className="rounded-md bg-indigo-500/10 border border-indigo-500/30 px-1.5 py-0.5 text-[11px] text-indigo-300"
                        >
                          {authority.pinpoint ?? authority.title}
                        </span>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </Section>

        {/* Sources */}
        <Section title="Sources">
          {sources.length === 0 ? (
            <p className="text-xs text-gray-600">No live grounding sources returned yet.</p>
          ) : (
            <div className="space-y-2">
              {sources.slice(0, 4).map((source) => (
                <article
                  key={`${source.tool}-${source.title}-${source.pinpoint ?? ""}`}
                  className="rounded-2xl border border-gray-800 bg-gray-950 p-3.5 text-xs"
                >
                  <div className="text-gray-200 font-medium leading-snug">
                    {source.url ? (
                      <a className="hover:text-indigo-300 underline-offset-2 hover:underline" href={source.url} rel="noreferrer" target="_blank">
                        {source.title}
                      </a>
                    ) : (
                      source.title
                    )}
                    {source.pinpoint ? <span className="text-gray-500 font-normal"> · {source.pinpoint}</span> : null}
                  </div>
                  {source.snippet ? (
                    <p className="mt-1 line-clamp-2 text-gray-600 leading-relaxed">{source.snippet}</p>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </Section>
      </div>

      {/* Tools status footer */}
      <div className="px-5 py-3.5 border-t border-gray-800 shrink-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.18em] text-gray-600 font-semibold mr-0.5">Tools</span>
          {(context?.tools ?? []).length === 0 ? (
            <span className="text-xs text-gray-600">—</span>
          ) : (
            (context?.tools ?? []).map((tool) => (
              <span
                key={tool.name}
                title={tool.detail}
                className={`inline-flex items-center gap-1.5 text-xs rounded-full border px-2.5 py-1 ${
                  tool.status === "ok"
                    ? "border-emerald-700/50 bg-emerald-950/30 text-emerald-300"
                    : tool.status === "error"
                    ? "border-rose-800/50 bg-rose-950/30 text-rose-300"
                    : "border-gray-700 bg-gray-950 text-gray-500"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    tool.status === "ok" ? "bg-emerald-400" : tool.status === "error" ? "bg-rose-400" : "bg-gray-600"
                  }`}
                />
                {TOOL_LABELS[tool.name] ?? tool.name}
              </span>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}

function RadarIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}

function RefreshIcon({ spinning }: { spinning: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={spinning ? "animate-spin" : ""}
    >
      <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
      <path d="M3 21v-5h5" />
    </svg>
  );
}
