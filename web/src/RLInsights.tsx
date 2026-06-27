/**
 * The grounded-estimator panel for the Debrief (THEORY_ADDENDUM.md).
 * Renders the win-probability curve (absorbing-Markov V(s)) with the
 * max-regret turning point marked, the calibration read (ECE), the IRT skill
 * estimate θ, and the next-round zone-of-proximal-development target.
 */

export interface SkillDimension {
  label: string;
  theta: number;
  delta: number;
  uncertainty: number;
}

export interface RLInsightsData {
  win_prob_trajectory: number[];
  regret_by_turn: number[];
  max_regret_turn: number;
  final_win_prob: number;
  calibration_error: number | null;
  calibration_note: string;
  skill: SkillDimension[];
  skill_scalar: number;
  target_success: number;
  recommended_aggression_delta: number;
  zpd_note: string;
}

function WinProbCurve({ traj, tpTurn }: { traj: number[]; tpTurn: number }) {
  if (traj.length === 0) return null;
  const w = 320;
  const h = 96;
  const pad = 10;
  const innerW = w - pad * 2;
  const innerH = h - pad * 2;
  const xs = traj.map((_, i) => pad + (i / Math.max(traj.length - 1, 1)) * innerW);
  const ys = traj.map((v) => pad + (1 - v) * innerH);
  const polyline = xs.map((x, i) => `${x},${ys[i]}`).join(" ");
  const area = [`${xs[0]},${h - pad}`, ...xs.map((x, i) => `${x},${ys[i]}`), `${xs[xs.length - 1]},${h - pad}`].join(" ");
  const midY = pad + 0.5 * innerH;
  const tpIdx = tpTurn - 1;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-24" preserveAspectRatio="none">
      <polygon points={area} fill="rgba(16,185,129,0.10)" />
      {/* 50% reference line */}
      <line x1={pad} y1={midY} x2={w - pad} y2={midY} stroke="rgba(148,163,184,0.25)" strokeWidth="1" strokeDasharray="3 3" />
      <polyline points={polyline} fill="none" stroke="#34d399" strokeWidth="2" strokeLinejoin="round" />
      {xs.map((x, i) => (
        <circle key={i} cx={x} cy={ys[i]} r={i === tpIdx ? 4.5 : 2.5} fill={i === tpIdx ? "#f59e0b" : "#34d399"} />
      ))}
      {tpIdx >= 0 && tpIdx < xs.length && (
        <line x1={xs[tpIdx]} y1={pad} x2={xs[tpIdx]} y2={h - pad} stroke="rgba(245,158,11,0.4)" strokeWidth="1" />
      )}
    </svg>
  );
}

function CalibrationGauge({ ece }: { ece: number | null }) {
  if (ece === null) return <span className="text-gray-500 text-sm">No citations to calibrate</span>;
  const pct = Math.round((1 - ece) * 100); // calibration quality
  const color = ece < 0.12 ? "text-emerald-400" : ece < 0.3 ? "text-amber-400" : "text-rose-400";
  const bar = ece < 0.12 ? "bg-emerald-500" : ece < 0.3 ? "bg-amber-400" : "bg-rose-500";
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className={`text-2xl font-black tabular-nums ${color}`}>{pct}%</span>
        <span className="text-xs text-gray-500">calibrated · ECE {ece.toFixed(2)}</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function RLInsights({ rl }: { rl: RLInsightsData }) {
  return (
    <section className="bg-gray-900 border border-gray-700 rounded-xl p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div className="text-xs text-emerald-400 font-semibold uppercase tracking-widest">
          Win-probability model
        </div>
        <span className="text-xs text-gray-500 tabular-nums">
          ended {Math.round(rl.final_win_prob * 100)}%
        </span>
      </div>

      {/* V(s) curve with the max-regret turning point marked */}
      <div>
        <WinProbCurve traj={rl.win_prob_trajectory} tpTurn={rl.max_regret_turn} />
        <p className="text-xs text-gray-500 mt-1">
          P(good outcome) per turn, from the absorbing-Markov value function.
          <span className="text-amber-400"> ◆ Turn {rl.max_regret_turn}</span> destroyed the most
          win-probability — your turning point.
        </p>
      </div>

      {/* Calibration (ECE) */}
      <div className="border-t border-gray-800 pt-4">
        <div className="text-xs text-gray-500 font-semibold uppercase tracking-widest mb-2">
          Epistemic calibration
        </div>
        <CalibrationGauge ece={rl.calibration_error} />
        <p className="text-xs text-gray-400 mt-2 leading-relaxed">{rl.calibration_note}</p>
      </div>

      {/* IRT skill estimate θ */}
      {rl.skill.length > 0 && (
        <div className="border-t border-gray-800 pt-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs text-gray-500 font-semibold uppercase tracking-widest">
              Skill estimate <span className="normal-case text-gray-600">(θ, Bayesian)</span>
            </div>
            <span className="text-xs text-gray-500">mastery {Math.round(rl.skill_scalar * 100)}%</span>
          </div>
          <div className="space-y-2.5">
            {rl.skill.map((d) => {
              const pct = Math.round(d.theta * 100);
              const up = d.delta >= 0;
              return (
                <div key={d.label}>
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>{d.label}</span>
                    <span className="flex items-center gap-2 tabular-nums">
                      <span>{pct}%</span>
                      {Math.abs(d.delta) >= 0.005 && (
                        <span className={up ? "text-emerald-400" : "text-rose-400"}>
                          {up ? "▲" : "▼"} {Math.abs(Math.round(d.delta * 100))}
                        </span>
                      )}
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

      {/* ZPD next-round target */}
      {rl.zpd_note && (
        <div className="border-t border-gray-800 pt-4">
          <div className="text-xs text-indigo-400 font-semibold uppercase tracking-widest mb-1.5">
            Next round · calibrated difficulty
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">{rl.zpd_note}</p>
        </div>
      )}
    </section>
  );
}
