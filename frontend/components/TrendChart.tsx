/** Dependency-free sparkline of the daily democracy indicator. */
export default function TrendChart({
  series,
}: {
  series: { date: string; net_direction: number }[];
}) {
  if (!series.length) return null;
  const w = 860;
  const h = 90;
  const step = w / Math.max(series.length - 1, 1);
  const y = (v: number) => h / 2 - (Math.max(-1, Math.min(1, v)) * h) / 2.4;
  const path = series.map((p, i) => `${i ? "L" : "M"}${i * step},${y(p.net_direction)}`).join(" ");

  return (
    <div className="card">
      <div className="small muted" style={{ marginBottom: 8 }}>
        Democracy indicator — last {series.length} digests (below the line = erosion)
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="img"
           aria-label="Democracy indicator trend">
        <line x1="0" y1={h / 2} x2={w} y2={h / 2} stroke="var(--line)" strokeWidth="1" />
        <path d={path} fill="none" stroke="var(--accent)" strokeWidth="2" />
        {series.map((p, i) => (
          <circle key={p.date} cx={i * step} cy={y(p.net_direction)} r="2.5"
                  fill={p.net_direction < 0 ? "var(--erosion)" : "var(--strengthen)"} />
        ))}
      </svg>
    </div>
  );
}
