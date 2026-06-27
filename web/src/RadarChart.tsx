export interface RadarAxis {
  label: string;
  value: number;
}

interface Props {
  axes: RadarAxis[];
  max?: number;
  size?: number;
  color?: string;
  fillOpacity?: number;
  compareAxes?: RadarAxis[];
  compareColor?: string;
  className?: string;
}

function polarPoint(cx: number, cy: number, r: number, i: number, n: number) {
  // 0 = top (12 o'clock), clockwise
  const angle = (2 * Math.PI * i) / n - Math.PI / 2;
  return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
}

function toPolygonPoints(
  cx: number, cy: number, r: number,
  values: number[], maxVal: number, n: number
): string {
  return values
    .map((v, i) => {
      const ratio = Math.max(0, Math.min(1, v / maxVal));
      const p = polarPoint(cx, cy, r * ratio, i, n);
      return `${p.x.toFixed(2)},${p.y.toFixed(2)}`;
    })
    .join(" ");
}

export default function RadarChart({
  axes,
  max = 1,
  size = 220,
  color = "#6366f1",
  fillOpacity = 0.28,
  compareAxes,
  compareColor = "#f59e0b",
  className = "",
}: Props) {
  const n = axes.length;
  if (n < 3) return null;

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.36;
  const labelR = size * 0.47;
  const gridLevels = [0.25, 0.5, 0.75, 1.0];

  const gridPoints = (level: number) =>
    Array.from({ length: n }, (_, i) => {
      const p = polarPoint(cx, cy, r * level, i, n);
      return `${p.x.toFixed(2)},${p.y.toFixed(2)}`;
    }).join(" ");

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
    >
      {/* Grid rings */}
      {gridLevels.map((level) => (
        <polygon
          key={level}
          points={gridPoints(level)}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth="1"
        />
      ))}

      {/* Spokes */}
      {axes.map((_, i) => {
        const p = polarPoint(cx, cy, r, i, n);
        return (
          <line
            key={i}
            x1={cx} y1={cy}
            x2={p.x.toFixed(2)} y2={p.y.toFixed(2)}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="1"
          />
        );
      })}

      {/* Comparison polygon (drawn first, behind main) */}
      {compareAxes && compareAxes.length === n && (
        <polygon
          points={toPolygonPoints(cx, cy, r, compareAxes.map((a) => a.value), max, n)}
          fill={compareColor}
          fillOpacity={0.1}
          stroke={compareColor}
          strokeWidth="1.5"
          strokeOpacity={0.45}
          strokeDasharray="3 2"
        />
      )}

      {/* Main filled polygon */}
      <polygon
        points={toPolygonPoints(cx, cy, r, axes.map((a) => a.value), max, n)}
        fill={color}
        fillOpacity={fillOpacity}
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
      />

      {/* Vertex dots */}
      {axes.map((a, i) => {
        const ratio = Math.max(0, Math.min(1, a.value / max));
        const p = polarPoint(cx, cy, r * ratio, i, n);
        return (
          <circle key={i} cx={p.x.toFixed(2)} cy={p.y.toFixed(2)} r="3.5" fill={color} />
        );
      })}

      {/* Axis labels */}
      {axes.map((a, i) => {
        const p = polarPoint(cx, cy, labelR, i, n);
        const anchor =
          p.x < cx - 8 ? "end" : p.x > cx + 8 ? "start" : "middle";
        return (
          <text
            key={i}
            x={p.x.toFixed(2)}
            y={p.y.toFixed(2)}
            textAnchor={anchor}
            dominantBaseline="central"
            fontSize="9"
            fill="rgba(156,163,175,0.9)"
            fontFamily="system-ui, sans-serif"
          >
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}
