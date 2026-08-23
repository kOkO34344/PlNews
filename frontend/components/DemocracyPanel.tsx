import type { StoryAnalysis } from "@/lib/api";

const LABEL: Record<number, string> = {
  [-2]: "severe erosion", [-1]: "erosion", 0: "neutral / mixed",
  1: "strengthening", 2: "significant strengthening",
};

export function tone(direction: number): "erosion" | "strengthen" | "" {
  if (direction < 0) return "erosion";
  if (direction > 0) return "strengthen";
  return "";
}

export default function DemocracyPanel({ analysis }: { analysis: StoryAnalysis }) {
  const dem = analysis.democracy;
  if (!dem.relevant) {
    return <p className="small muted">No significant democratic dimension.</p>;
  }
  const t = tone(dem.net_direction);
  return (
    <div className={`dem ${t}`}>
      <div>
        <span className={`badge ${t}`}>{LABEL[dem.net_direction] ?? "mixed"}</span>
        <span className="badge">significance {dem.significance.toFixed(2)}</span>
      </div>
      <ul className="small" style={{ margin: "8px 0 0", paddingLeft: 18 }}>
        {dem.impacts.map((i) => (
          <li key={i.dimension}>
            <strong>{i.dimension.replace(/_/g, " ")}</strong>{" "}
            {i.direction > 0 ? `+${i.direction}` : i.direction} — {i.rationale}{" "}
            <span className="muted">({Math.round(i.confidence * 100)}% conf.)</span>
          </li>
        ))}
      </ul>
      {dem.precedent && <p className="small muted">Precedent: {dem.precedent}</p>}
      {dem.watch_next.length > 0 && (
        <p className="small muted">Watch: {dem.watch_next.join("; ")}</p>
      )}
    </div>
  );
}
