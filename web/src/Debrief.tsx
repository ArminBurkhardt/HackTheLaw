import { useState } from "react";
import RadarChart from "./RadarChart";
import RLInsights, { type RLInsightsData } from "./RLInsights";
import { MOVE_ICON, MOVE_COLOR, classificationLabel } from "./arena/labels";

interface MoveEventData {
  turn: number;
  classification: string;
  refs: string[];
  position_delta: number;
  note: string;
}

interface TurningPointExchange {
  user_message: string;
  opponent_reply: string;
}

interface CitationCheck {
  status: "verified" | "weak" | "misattributed" | "fabricated_identifier" | "not_in_force";
  support: string;
  citation_score: number;
  confidence: number;
  note: string;
}

interface AuthorityData {
  title: string;
  pinpoint?: string;
  celex?: string;
  check?: CitationCheck | null;
}

interface DebriefData {
  score: number;
  subscores: Record<string, number>;
  score_to_beat: number | null;
  turning_point_turn: number;
  turning_point_explainer: string;
  turning_point_exchange: TurningPointExchange | null;
  stronger_move: string;
  stronger_move_authorities: AuthorityData[];
  biggest_concession: MoveEventData | null;
  biggest_miss: MoveEventData | null;
  biggest_overplay: MoveEventData | null;
  persona_note: string;
  user_citations: AuthorityData[];
  rl?: RLInsightsData | null;
}

interface Props {
  debrief: DebriefData;
  onRunAgain: () => void;
  onViewProgress?: () => void;
}

const SUBSCORE_LABELS: Record<string, string> = {
  outcome: "Outcome",
  must_haves: "Must-haves",
  concession_discipline: "Concession discipline",
  legal_grounding: "Legal grounding",
  composure: "Composure",
};

const SUBSCORE_MAX: Record<string, number> = {
  outcome: 35,
  must_haves: 25,
  concession_discipline: 20,
  legal_grounding: 15,
  composure: 5,
};

type Classification = keyof typeof MOVE_ICON;

function moveIcon(classification: string): string {
  return MOVE_ICON[classification as Classification] ?? "/icons/5_book.png";
}

function moveColor(classification: string): string {
  return MOVE_COLOR[classification as Classification] ?? "text-gray-400";
}

function verdict(score: number): { label: string; icon: string; tone: string } {
  if (score >= 85) return { label: "Brilliant round", icon: "/icons/0_brilliant.png", tone: "text-cyan-300" };
  if (score >= 70) return { label: "Strong round", icon: "/icons/2_best.png", tone: "text-emerald-400" };
  if (score >= 55) return { label: "Solid, with leaks", icon: "/icons/4_good.png", tone: "text-lime-300" };
  if (score >= 40) return { label: "Shaky — review below", icon: "/icons/6_inaccuracy.png", tone: "text-amber-400" };
  return { label: "Beaten this time", icon: "/icons/8_blunder.png", tone: "text-rose-400" };
}

const CITATION_STATUS: Record<
  CitationCheck["status"],
  { label: string; chip: string; dot: string }
> = {
  verified: { label: "verified", chip: "border-emerald-700/50 text-emerald-300", dot: "bg-emerald-400" },
  weak: { label: "weak", chip: "border-amber-700/50 text-amber-300", dot: "bg-amber-400" },
  misattributed: { label: "misattributed", chip: "border-rose-700/50 text-rose-300", dot: "bg-rose-400" },
  fabricated_identifier: { label: "not found", chip: "border-rose-700/50 text-rose-300", dot: "bg-rose-500" },
  not_in_force: { label: "repealed", chip: "border-orange-700/50 text-orange-300", dot: "bg-orange-400" },
};

/** An authority chip that surfaces its SECV verdict, if one was computed. */
function AuthorityChip({ authority }: { authority: AuthorityData }) {
  const check = authority.check;
  const meta = check ? CITATION_STATUS[check.status] : null;
  return (
    <span
      title={check?.note}
      className={`inline-flex items-center gap-1.5 text-xs rounded px-2 py-1 border ${
        meta ? `bg-gray-950/60 ${meta.chip}` : "bg-indigo-900/50 border-indigo-700/50 text-indigo-200"
      }`}
    >
      {meta && <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />}
      <span>
        {authority.title}
        {authority.pinpoint ? ` — ${authority.pinpoint}` : ""}
      </span>
      {meta && <span className="opacity-70">· {meta.label}</span>}
    </span>
  );
}

function ScoreBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>{label}</span>
        <span>
          {value}/{max}
        </span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/** A single thing the user did wrong, framed with a chess-style move glyph. */
function MistakeCard({ event, heading }: { event: MoveEventData; heading: string }) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 flex gap-3">
      <img
        src={moveIcon(event.classification)}
        alt={classificationLabel(event.classification as Classification)}
        className="w-7 h-7 shrink-0 mt-0.5"
      />
      <div className="min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-gray-100">{heading}</span>
          <span className={`text-xs font-medium ${moveColor(event.classification)}`}>
            {classificationLabel(event.classification as Classification)}
          </span>
          <span className="text-xs text-gray-600">· Turn {event.turn}</span>
        </div>
        <p className="text-sm text-gray-300 leading-relaxed">{event.note}</p>
        <div className="mt-1.5 flex items-center gap-2 text-xs text-gray-500">
          <span>
            Δ{event.position_delta > 0 ? "+" : ""}
            {event.position_delta.toFixed(2)}
          </span>
          {event.refs.length > 0 && (
            <span className="text-gray-600">· leaned on {event.refs.join(", ")}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function buildSkillsRadar(subscores: Record<string, number>) {
  return Object.entries(SUBSCORE_LABELS).map(([key, label]) => ({
    label,
    value: (subscores[key] ?? 0) / (SUBSCORE_MAX[key] ?? 1),
  }));
}

type SidebarTab = "scores" | "model" | "sources";

export default function Debrief({ debrief, onRunAgain, onViewProgress }: Props) {
  const [showFilmStudy, setShowFilmStudy] = useState(false);
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("scores");
  const beat = debrief.score_to_beat;
  const improved = beat !== null && debrief.score > beat;
  const skillsAxes = buildSkillsRadar(debrief.subscores);
  const v = verdict(debrief.score);

  const mistakes: Array<{ event: MoveEventData; heading: string }> = [];
  if (debrief.biggest_concession)
    mistakes.push({ event: debrief.biggest_concession, heading: "You conceded too early" });
  if (debrief.biggest_overplay)
    mistakes.push({ event: debrief.biggest_overplay, heading: "You overplayed your hand" });

  // Sources the opponent's playbook says you should have brought.
  const sources = debrief.stronger_move_authorities;
  // Authorities the trainee actually cited, each carrying its SECV verdict.
  const userCitations = debrief.user_citations ?? [];
  // Refs you actually leaned on at the moments things went wrong — candidates for misuse.
  const misusedRefs = Array.from(
    new Set(
      [debrief.biggest_concession, debrief.biggest_overplay, debrief.biggest_miss]
        .filter(Boolean)
        .flatMap((m) => (m as MoveEventData).refs)
    )
  );

  const sidebarTabs: { id: SidebarTab; label: string }[] = [
    { id: "scores", label: "Scores" },
    ...(debrief.rl ? [{ id: "model" as const, label: "Model" }] : []),
    { id: "sources", label: "Sources" },
  ];
  const activeTab = sidebarTab === "model" && !debrief.rl ? "scores" : sidebarTab;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-5xl mx-auto px-5 py-8">
        {/* ── Header band ───────────────────────────────────────── */}
        <header className="flex flex-col sm:flex-row items-center sm:items-end justify-between gap-4 mb-8">
          <div className="flex items-center gap-4">
            <img src={v.icon} alt="" className="w-14 h-14 shrink-0" />
            <div>
              <div className={`text-sm font-semibold ${v.tone}`}>{v.label}</div>
              <div className="text-xs text-gray-500 uppercase tracking-widest mt-0.5">Round debrief</div>
            </div>
          </div>
          <div className="text-center sm:text-right">
            <div className="text-6xl font-black tabular-nums tracking-tight leading-none">
              {debrief.score}
              <span className="text-2xl text-gray-500">/100</span>
            </div>
            {beat !== null && (
              <div
                className={`mt-1 text-sm font-medium ${improved ? "text-emerald-400" : "text-rose-400"}`}
              >
                {improved
                  ? `Beat your best by ${debrief.score - beat}`
                  : `${beat - debrief.score} short of your best (${beat})`}
              </div>
            )}
          </div>
        </header>

        <div className="grid lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] gap-6">
          {/* ── Left column: what went wrong ──────────────────── */}
          <div className="space-y-6">
            {/* What you did wrong */}
            <section>
              <h2 className="text-xs text-rose-400 font-semibold uppercase tracking-widest mb-3">
                What went wrong
              </h2>
              <div className="space-y-3">
                {mistakes.length > 0 ? (
                  mistakes.map((m, i) => (
                    <MistakeCard key={i} event={m.event} heading={m.heading} />
                  ))
                ) : (
                  <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-sm text-gray-400">
                    No major concessions or overplays this round — your discipline held. The leaks
                    were in missed opportunities (see below).
                  </div>
                )}
              </div>
            </section>

            {/* Deviation from the playbook */}
            <section>
              <h2 className="text-xs text-amber-400 font-semibold uppercase tracking-widest mb-3">
                Where you left the playbook
              </h2>
              {debrief.biggest_miss ? (
                <MistakeCard event={debrief.biggest_miss} heading="Missed playbook point" />
              ) : (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-sm text-gray-400">
                  You hit the playbook's required points. Tighten the margins to push the score
                  higher.
                </div>
              )}
            </section>

            {/* Turning point + film study */}
            <section className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-amber-500 font-semibold uppercase tracking-widest">
                  Turning point · Turn {debrief.turning_point_turn}
                </div>
                {debrief.turning_point_exchange && (
                  <button
                    onClick={() => setShowFilmStudy((s) => !s)}
                    className="text-xs text-amber-600 hover:text-amber-400 underline underline-offset-2"
                  >
                    {showFilmStudy ? "Hide replay" : "Film study ↓"}
                  </button>
                )}
              </div>
              <p className="text-amber-100 text-sm leading-relaxed">
                {debrief.turning_point_explainer}
              </p>

              {showFilmStudy && debrief.turning_point_exchange && (
                <div className="mt-4 space-y-3 border-t border-amber-800/30 pt-4">
                  <p className="text-xs text-amber-600 uppercase tracking-widest font-semibold">
                    What was said
                  </p>
                  <div className="flex flex-col items-end">
                    <div className="max-w-[85%] bg-indigo-700/60 rounded-2xl rounded-br-sm px-4 py-2 text-sm text-white leading-relaxed whitespace-pre-wrap">
                      {debrief.turning_point_exchange.user_message}
                    </div>
                    <span className="text-xs text-gray-600 mt-1">You</span>
                  </div>
                  <div className="flex flex-col items-start">
                    <div className="max-w-[85%] bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-2 text-sm text-gray-100 leading-relaxed whitespace-pre-wrap">
                      {debrief.turning_point_exchange.opponent_reply}
                    </div>
                    <span className="text-xs text-gray-600 mt-1">Opponent</span>
                  </div>
                </div>
              )}
            </section>

            {/* The great-lawyer move */}
            <section className="bg-indigo-950/30 border border-indigo-800/40 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <img src="/icons/1_great.png" alt="" className="w-5 h-5" />
                <div className="text-xs text-indigo-400 font-semibold uppercase tracking-widest">
                  The great-lawyer move instead
                </div>
              </div>
              <p className="text-indigo-100 text-sm leading-relaxed">{debrief.stronger_move}</p>
            </section>
          </div>

          {/* ── Right column: tabbed so it stays compact ──────── */}
          <div className="space-y-4 lg:sticky lg:top-6 self-start">
            {/* Segmented control */}
            <div className="flex gap-1 bg-gray-900 border border-gray-700 rounded-xl p-1">
              {sidebarTabs.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSidebarTab(t.id)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-widest transition-colors ${
                    activeTab === t.id
                      ? "bg-gray-700 text-gray-100"
                      : "text-gray-500 hover:text-gray-300"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Scores: radar + rubric breakdown */}
            {activeTab === "scores" && (
              <section className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <div className="flex justify-center mb-4">
                  <RadarChart axes={skillsAxes} max={1} size={180} color="#6366f1" fillOpacity={0.28} />
                </div>
                <div className="space-y-3">
                  {Object.entries(debrief.subscores).map(([key, val]) => (
                    <ScoreBar
                      key={key}
                      label={SUBSCORE_LABELS[key] ?? key}
                      value={val}
                      max={SUBSCORE_MAX[key] ?? 100}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* Model: grounded RL estimators (value/regret, calibration, skill, ZPD) */}
            {activeTab === "model" && debrief.rl && <RLInsights rl={debrief.rl} />}

            {/* Sources */}
            {activeTab === "sources" && (
              <section className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <div className="text-xs text-gray-500 font-semibold uppercase tracking-widest mb-3">
                  Authorities & sources
                </div>
                {sources.length > 0 ? (
                  <>
                    <p className="text-xs text-gray-500 mb-2">You should have grounded on:</p>
                    <div className="flex flex-wrap gap-2">
                      {sources.map((a, i) => (
                        <AuthorityChip key={i} authority={a} />
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-gray-500">
                    No additional authorities flagged for the turning point.
                  </p>
                )}

                {userCitations.length > 0 && (
                  <div className="mt-4 border-t border-gray-800 pt-3">
                    <p className="text-xs text-gray-400 mb-2">
                      Your citations <span className="text-gray-600">· checked against source by SECV</span>
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {userCitations.map((a, i) => (
                        <AuthorityChip key={i} authority={a} />
                      ))}
                    </div>
                  </div>
                )}

                {misusedRefs.length > 0 && (
                  <div className="mt-4 border-t border-gray-800 pt-3">
                    <p className="text-xs text-rose-400 mb-2">Sources you leaned on as things slipped:</p>
                    <div className="flex flex-wrap gap-2">
                      {misusedRefs.map((r, i) => (
                        <span
                          key={i}
                          className="text-xs bg-rose-950/40 border border-rose-800/40 rounded px-2 py-1 text-rose-200"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* Persona note — always visible, it's short and sets the tone */}
            {debrief.persona_note && (
              <div className="text-sm text-gray-400 italic border-l-2 border-gray-700 pl-4">
                {debrief.persona_note}
              </div>
            )}
          </div>
        </div>

        {/* ── Actions ───────────────────────────────────────────── */}
        <div className="mt-10 flex flex-col sm:flex-row gap-3">
          <button
            onClick={onRunAgain}
            className="flex-1 py-3.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-semibold tracking-tight text-white shadow-lg shadow-indigo-900/30 transition-colors"
          >
            Run it again — beat {debrief.score}
          </button>
          {onViewProgress && (
            <button
              onClick={onViewProgress}
              className="sm:w-56 py-3.5 bg-gray-800 hover:bg-gray-700 rounded-xl text-sm font-medium text-gray-200 tracking-tight transition-colors"
            >
              View progress
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
