import { useState } from "react";
import RadarChart from "./RadarChart";

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

interface DebriefData {
  score: number;
  subscores: Record<string, number>;
  score_to_beat: number | null;
  turning_point_turn: number;
  turning_point_explainer: string;
  turning_point_exchange: TurningPointExchange | null;
  stronger_move: string;
  stronger_move_authorities: Array<{ title: string; pinpoint?: string; celex?: string }>;
  biggest_concession: MoveEventData | null;
  biggest_miss: MoveEventData | null;
  biggest_overplay: MoveEventData | null;
  persona_note: string;
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

function MoveCard({ event, label }: { event: MoveEventData; label: string }) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-sm">
      <div className="text-xs text-gray-500 mb-1">
        {label} · Turn {event.turn}
      </div>
      <div className="text-gray-200">{event.note}</div>
      <div className="text-xs text-gray-500 mt-1">
        Δ{event.position_delta > 0 ? "+" : ""}
        {event.position_delta.toFixed(2)}
        {event.refs.length > 0 && ` · ${event.refs.join(", ")}`}
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

export default function Debrief({ debrief, onRunAgain, onViewProgress }: Props) {
  const [showFilmStudy, setShowFilmStudy] = useState(false);
  const beat = debrief.score_to_beat;
  const improved = beat !== null && debrief.score > beat;
  const skillsAxes = buildSkillsRadar(debrief.subscores);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6 max-w-2xl mx-auto">
      {/* Score */}
      <div className="text-center mb-8">
        <div className="text-6xl font-black tabular-nums tracking-tight">
          {debrief.score}
          <span className="text-2xl text-gray-500">/100</span>
        </div>
        {beat !== null && (
          <div
            className={`mt-2 text-sm font-medium ${improved ? "text-emerald-400" : "text-rose-400"}`}
          >
            {improved
              ? `Beat your best by ${debrief.score - beat} points`
              : `Previous best: ${beat} — ${beat - debrief.score} points short`}
          </div>
        )}
      </div>

      {/* Skills radar + subscores side by side */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
        <div className="text-xs text-gray-500 font-semibold uppercase tracking-widest mb-4">
          Skills this round
        </div>
        <div className="flex gap-6 items-center">
          {/* Radar */}
          <div className="shrink-0">
            <RadarChart
              axes={skillsAxes}
              max={1}
              size={160}
              color="#6366f1"
              fillOpacity={0.28}
            />
          </div>
          {/* Bars */}
          <div className="flex-1 space-y-3">
            {Object.entries(debrief.subscores).map(([key, val]) => (
              <ScoreBar
                key={key}
                label={SUBSCORE_LABELS[key] ?? key}
                value={val}
                max={SUBSCORE_MAX[key] ?? 100}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Turning point */}
      <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-5 mb-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs text-amber-500 font-semibold uppercase tracking-widest">
            Turning point · Turn {debrief.turning_point_turn}
          </div>
          {debrief.turning_point_exchange && (
            <button
              onClick={() => setShowFilmStudy((v) => !v)}
              className="text-xs text-amber-600 hover:text-amber-400 underline underline-offset-2"
            >
              {showFilmStudy ? "Hide replay" : "Film study ↓"}
            </button>
          )}
        </div>
        <p className="text-amber-100 text-sm leading-relaxed">{debrief.turning_point_explainer}</p>

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
            <div className="bg-indigo-950/50 border border-indigo-700/40 rounded-xl p-3 mt-2">
              <p className="text-xs text-indigo-400 font-semibold uppercase tracking-widest mb-1">
                Great-lawyer move instead
              </p>
              <p className="text-sm text-indigo-100 leading-relaxed">{debrief.stronger_move}</p>
            </div>
          </div>
        )}
      </div>

      {/* Stronger move (standalone when film study is hidden) */}
      {!showFilmStudy && (
        <div className="bg-indigo-950/30 border border-indigo-800/40 rounded-xl p-5 mb-6">
          <div className="text-xs text-indigo-400 font-semibold uppercase tracking-widest mb-2">
            The great-lawyer move
          </div>
          <p className="text-indigo-100 text-sm leading-relaxed">{debrief.stronger_move}</p>
          {debrief.stronger_move_authorities.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {debrief.stronger_move_authorities.map((a, i) => (
                <span
                  key={i}
                  className="text-xs bg-indigo-900/60 border border-indigo-700/50 rounded px-2 py-1 text-indigo-300"
                >
                  {a.title}
                  {a.pinpoint ? ` — ${a.pinpoint}` : ""}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {showFilmStudy && debrief.stronger_move_authorities.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {debrief.stronger_move_authorities.map((a, i) => (
            <span
              key={i}
              className="text-xs bg-indigo-900/60 border border-indigo-700/50 rounded px-2 py-1 text-indigo-300"
            >
              {a.title}
              {a.pinpoint ? ` — ${a.pinpoint}` : ""}
            </span>
          ))}
        </div>
      )}

      {/* Biggest events */}
      <div className="space-y-3 mb-6">
        {debrief.biggest_concession && (
          <MoveCard event={debrief.biggest_concession} label="Biggest concession" />
        )}
        {debrief.biggest_miss && (
          <MoveCard event={debrief.biggest_miss} label="Biggest missed opportunity" />
        )}
        {debrief.biggest_overplay && (
          <MoveCard event={debrief.biggest_overplay} label="Biggest overplay" />
        )}
      </div>

      {/* Persona note */}
      {debrief.persona_note && (
        <div className="text-sm text-gray-400 italic border-l-2 border-gray-700 pl-4 mb-8">
          {debrief.persona_note}
        </div>
      )}

      {/* Action buttons */}
      <div className="space-y-3">
        <button
          onClick={onRunAgain}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-semibold tracking-tight"
        >
          Run it again — beat {debrief.score}
        </button>
        {onViewProgress && (
          <button
            onClick={onViewProgress}
            className="w-full py-2.5 bg-gray-800 hover:bg-gray-700 rounded-xl text-sm text-gray-300 tracking-tight"
          >
            View progress
          </button>
        )}
      </div>
    </div>
  );
}
