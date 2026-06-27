/**
 * The "current standing" tug-of-war shown in the command bar.
 * Centre = neutral; the glowing marker slides toward whoever holds ground.
 */
export default function StandingBar({
  position,
  winProbability,
}: {
  position: number;
  winProbability?: number | null;
}) {
  const clamped = Math.max(-5, Math.min(5, position));
  const pct = ((clamped + 5) / 10) * 100; // 0..100, 50 = neutral
  const onYourSide = clamped > 0;
  const hasWin = typeof winProbability === "number";
  const winPct = hasWin ? Math.round((winProbability as number) * 100) : null;

  const tone =
    clamped > 1
      ? { fill: "bg-emerald-500", glow: "shadow-emerald-500/50", text: "text-emerald-400", dot: "bg-emerald-400" }
      : clamped < -1
      ? { fill: "bg-rose-500", glow: "shadow-rose-500/50", text: "text-rose-400", dot: "bg-rose-400" }
      : { fill: "bg-amber-400", glow: "shadow-amber-400/50", text: "text-amber-400", dot: "bg-amber-400" };

  const label = clamped > 1 ? "Gaining ground" : clamped < -1 ? "Losing ground" : "Holding even";

  // Fill stretches from the centre out toward the current position.
  const fillLeft = onYourSide ? 50 : pct;
  const fillWidth = Math.abs(pct - 50);

  return (
    <div className="w-full select-none">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] uppercase tracking-[0.15em] text-gray-600 font-medium">Their ground</span>
        <span className={`flex items-center gap-1.5 text-[11px] font-semibold ${tone.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${tone.dot} animate-pulse`} />
          {label}
          {winPct !== null && (
            <span
              title="Absorbing-Markov win probability from your current standing"
              className="ml-1 text-gray-500 font-medium tabular-nums"
            >
              · {winPct}% win
            </span>
          )}
        </span>
        <span className="text-[10px] uppercase tracking-[0.15em] text-gray-600 font-medium">Your ground</span>
      </div>

      <div className="relative h-2.5 rounded-full bg-gray-800/80 overflow-visible">
        {/* centre notch */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-3 rounded-full bg-gray-600" />
        {/* directional fill from centre */}
        <div
          className={`absolute top-0 h-full rounded-full ${tone.fill} transition-all duration-500`}
          style={{ left: `${fillLeft}%`, width: `${fillWidth}%` }}
        />
        {/* glowing marker */}
        <div
          className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-white shadow-lg ${tone.glow} ring-2 ring-gray-950 transition-all duration-500`}
          style={{ left: `${pct}%` }}
        />
      </div>
    </div>
  );
}
