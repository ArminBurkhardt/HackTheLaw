import RadarChart from "./RadarChart";

interface RoundEntry {
  scenario: string;
  persona: string;
  score: number;
  logged_at: string;
}

interface SkillDimension {
  label: string;
  theta: number;
  uncertainty: number;
}

interface ProgressData {
  scores: number[];
  streak: number;
  weak_vs_persona: Record<string, number>;
  recurring_weaknesses: string[];
  history: RoundEntry[];
  latest_subscores: Record<string, number>;
  skill?: SkillDimension[];
}

interface Props {
  data: ProgressData;
  scoreToBeat: number | null;
  onBack: () => void;
}

const PERSONA_LABELS: Record<string, string> = {
  aggressor: "Aggressor",
  charmer: "Charmer",
  stonewaller: "Stonewaller",
  technician: "Technician",
};

const SUBSCORE_LABELS: Record<string, string> = {
  outcome: "Outcome",
  must_haves: "Must-haves",
  concession_discipline: "Conc. discipline",
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

function MiniSparkline({ scores, scoreToBeat }: { scores: number[]; scoreToBeat: number | null }) {
  if (scores.length === 0) return <p className="text-gray-500 text-sm">No rounds yet.</p>;

  const w = 480;
  const h = 100;
  const pad = 12;
  const innerW = w - pad * 2;
  const innerH = h - pad * 2;

  const xs = scores.map((_, i) => pad + (i / Math.max(scores.length - 1, 1)) * innerW);
  const ys = scores.map((s) => pad + (1 - s / 100) * innerH);

  const polyline = xs.map((x, i) => `${x},${ys[i]}`).join(" ");
  const areaPoints = [
    `${xs[0]},${h - pad}`,
    ...xs.map((x, i) => `${x},${ys[i]}`),
    `${xs[xs.length - 1]},${h - pad}`,
  ].join(" ");

  const beatY =
    scoreToBeat !== null ? pad + (1 - scoreToBeat / 100) * innerH : null;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-24" preserveAspectRatio="none">
      <polygon points={areaPoints} fill="rgba(99,102,241,0.12)" />
      {beatY !== null && (
        <>
          <line
            x1={pad} y1={beatY} x2={w - pad} y2={beatY}
            stroke="rgba(251,191,36,0.5)"
            strokeWidth="1"
            strokeDasharray="4 3"
          />
          <text x={w - pad + 2} y={beatY + 4} fill="rgba(251,191,36,0.7)" fontSize="9">
            best
          </text>
        </>
      )}
      <polyline
        points={polyline}
        fill="none"
        stroke="#6366f1"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {xs.map((x, i) => (
        <circle key={i} cx={x} cy={ys[i]} r="3" fill="#6366f1" />
      ))}
    </svg>
  );
}

function PersonaBar({ label, weakness }: { label: string; weakness: number }) {
  const mastery = Math.round((1 - weakness) * 100);
  const color =
    mastery >= 70 ? "bg-emerald-500" : mastery >= 40 ? "bg-amber-400" : "bg-rose-500";

  return (
    <div>
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>{label}</span>
        <span>{mastery}% mastery</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${mastery}%` }}
        />
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

export default function Progress({ data, scoreToBeat, onBack }: Props) {
  const best = data.scores.length > 0 ? Math.max(...data.scores) : null;
  const latest = data.scores.length > 0 ? data.scores[data.scores.length - 1] : null;
  const personaEntries = Object.entries(data.weak_vs_persona);
  const hasSubscores = Object.keys(data.latest_subscores ?? {}).length > 0;
  const skillsAxes = hasSubscores ? buildSkillsRadar(data.latest_subscores) : null;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Progress</h1>
        <button onClick={onBack} className="text-sm text-gray-400 hover:text-gray-200">
          ← Back
        </button>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
          <div className="text-3xl font-black tabular-nums">{data.streak}</div>
          <div className="text-xs text-gray-500 mt-1">Streak</div>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
          <div className="text-3xl font-black tabular-nums">{best ?? "—"}</div>
          <div className="text-xs text-gray-500 mt-1">Best score</div>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
          <div className="text-3xl font-black tabular-nums">{data.scores.length}</div>
          <div className="text-xs text-gray-500 mt-1">Rounds</div>
        </div>
      </div>

      {/* Performance profile — hero radar */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
        <div className="text-xs text-indigo-400 font-semibold uppercase tracking-widest mb-4">
          Performance profile
        </div>
        {skillsAxes ? (
          <div className="flex flex-col sm:flex-row gap-6 items-center">
            <div className="shrink-0">
              <RadarChart
                axes={skillsAxes}
                max={1}
                size={200}
                color="#6366f1"
                fillOpacity={0.28}
              />
            </div>
            <div className="flex-1 w-full space-y-3">
              {skillsAxes.map((ax) => (
                <div key={ax.label}>
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>{ax.label}</span>
                    <span>{Math.round(ax.value * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${
                        ax.value >= 0.7
                          ? "bg-emerald-500"
                          : ax.value >= 0.4
                          ? "bg-amber-400"
                          : "bg-rose-500"
                      }`}
                      style={{ width: `${ax.value * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            Complete a round to chart your performance across outcome, must-haves,
            concession discipline, legal grounding, and composure.
          </p>
        )}
      </div>

      {/* Skill estimate θ — Bayesian posterior with uncertainty */}
      {data.skill && data.skill.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs text-emerald-400 font-semibold uppercase tracking-widest">
              Skill estimate <span className="normal-case text-gray-600">(θ, IRT)</span>
            </div>
            <span className="text-xs text-gray-600">± shows confidence</span>
          </div>
          <div className="space-y-3">
            {data.skill.map((d) => {
              const pct = Math.round(d.theta * 100);
              const band = Math.round(Math.min(d.uncertainty, 2) * 25); // logit-std → rough %
              return (
                <div key={d.label}>
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>{d.label}</span>
                    <span className="tabular-nums">
                      {pct}% <span className="text-gray-600">± {band}</span>
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${
                        d.theta >= 0.7 ? "bg-emerald-500" : d.theta >= 0.4 ? "bg-amber-400" : "bg-rose-500"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Score trend */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
        <div className="text-xs text-gray-500 font-semibold uppercase tracking-widest mb-3">
          Score trend
        </div>
        {data.scores.length < 2 ? (
          <p className="text-sm text-gray-500">Complete at least 2 rounds to see the trend.</p>
        ) : (
          <>
            <MiniSparkline scores={data.scores} scoreToBeat={scoreToBeat ?? best} />
            <div className="flex justify-between text-xs text-gray-600 mt-1">
              <span>Round 1</span>
              <span>Round {data.scores.length}</span>
            </div>
          </>
        )}
        {latest !== null && (
          <div className="mt-3 text-xs text-gray-400">
            Latest:{" "}
            <span className="text-white font-semibold">{latest}</span>
            {best !== null && best !== latest && (
              <span className="ml-2 text-amber-400">Best: {best}</span>
            )}
          </div>
        )}
      </div>

      {/* Per-persona breakdown */}
      {personaEntries.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
          <div className="text-xs text-gray-500 font-semibold uppercase tracking-widest mb-3">
            Persona mastery
          </div>
          <div className="space-y-3">
            {personaEntries.map(([p, weakness]) => (
              <PersonaBar
                key={p}
                label={PERSONA_LABELS[p] ?? p}
                weakness={weakness}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recurring weaknesses */}
      {data.recurring_weaknesses.length > 0 && (
        <div className="bg-rose-950/20 border border-rose-800/30 rounded-xl p-5 mb-6">
          <div className="text-xs text-rose-400 font-semibold uppercase tracking-widest mb-3">
            Recurring weaknesses
          </div>
          <ul className="space-y-2">
            {data.recurring_weaknesses.map((w, i) => (
              <li key={i} className="text-sm text-rose-200 flex gap-2">
                <span className="text-rose-500 mt-0.5">·</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Round history */}
      {data.history.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <div className="text-xs text-gray-500 font-semibold uppercase tracking-widest mb-3">
            Round history
          </div>
          <div className="space-y-2">
            {[...data.history].reverse().map((r, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="text-gray-300">
                  <span className="capitalize">{r.scenario}</span>
                  <span className="text-gray-600 mx-1">·</span>
                  <span className="text-gray-500 capitalize">
                    {PERSONA_LABELS[r.persona] ?? r.persona}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-semibold tabular-nums">{r.score}</span>
                  <span className="text-xs text-gray-600">
                    {new Date(r.logged_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.scores.length === 0 && (
        <div className="text-center text-gray-500 text-sm mt-12">
          Complete a round to see your progress.
        </div>
      )}
    </div>
  );
}
