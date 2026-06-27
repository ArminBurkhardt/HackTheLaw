export default function TensionMeter({ position }: { position: number }) {
  const clamped = Math.max(-5, Math.min(5, position));
  const pct = ((clamped + 5) / 10) * 100; // 0..100, 50 = neutral
  const onYourSide = clamped > 0;
  const color =
    clamped > 1 ? "bg-emerald-500" : clamped < -1 ? "bg-rose-500" : "bg-amber-400";
  const thumbColor =
    clamped > 1 ? "bg-emerald-400" : clamped < -1 ? "bg-rose-400" : "bg-amber-300";

  // Fill stretches from the centre out toward the current position.
  const fillLeft = onYourSide ? 50 : pct;
  const fillWidth = Math.abs(pct - 50);

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Their ground</span>
        <span>Neutral</span>
        <span>Your ground</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full relative">
        {/* centre tick */}
        <div className="absolute left-1/2 top-0 -translate-x-1/2 w-px h-full bg-gray-600" />
        {/* directional fill from centre */}
        <div
          className={`absolute top-0 h-full rounded-full transition-all duration-500 ${color}`}
          style={{ left: `${fillLeft}%`, width: `${fillWidth}%` }}
        />
        {/* position thumb */}
        <div
          className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full ring-2 ring-gray-950 shadow transition-all duration-500 ${thumbColor}`}
          style={{ left: `${pct}%` }}
        />
      </div>
    </div>
  );
}
