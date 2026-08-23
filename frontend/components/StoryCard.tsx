import type { DigestItem } from "@/lib/api";
import DemocracyPanel from "./DemocracyPanel";

const LEAN_LABEL: Record<string, string> = {
  left: "L", center_left: "CL", center: "C", center_right: "CR", right: "R",
  state_aligned: "state", oligarch_linked: "oligarch", unknown: "?",
};

export default function StoryCard({ item }: { item: DigestItem }) {
  const a = item.analysis;
  return (
    <article className="card">
      <h3>
        <span className="rank">{item.rank}.</span>
        {a.headline}
      </h3>

      <p>{a.what_happened}</p>
      <p className="small">
        <strong>Why it matters.</strong> {a.why_it_matters}
      </p>

      <DemocracyPanel analysis={a} />

      <div className="bias">
        <strong>Framing check.</strong> {a.bias.coverage_spread}
        {a.bias.framing_devices.length > 0 && (
          <div className="small muted">Devices: {a.bias.framing_devices.join("; ")}</div>
        )}
        {a.bias.omitted_context.length > 0 && (
          <div className="small muted">Missing: {a.bias.omitted_context.join("; ")}</div>
        )}
        <div className="small muted">
          Source diversity {a.bias.source_diversity.toFixed(2)} · credibility{" "}
          {a.credibility.toFixed(2)} · novelty {a.novelty.toFixed(2)}
        </div>
      </div>

      {a.uncertainty && (
        <p className="small">
          <strong>Unknown.</strong> {a.uncertainty}
        </p>
      )}
      {a.contrarian_read && (
        <details>
          <summary>Strongest counter-reading</summary>
          <p className="small">{a.contrarian_read}</p>
        </details>
      )}

      <div className="sources">
        {item.refs.map((r) => (
          <span key={r.url}>
            <a href={r.url} target="_blank" rel="noreferrer">
              {r.source_name}
            </a>{" "}
            <span className="badge">{LEAN_LABEL[r.lean] ?? r.lean}</span>
          </span>
        ))}
      </div>

      <details>
        <summary>Why this was selected — {item.score.total.toFixed(3)}</summary>
        <p className="small muted">{item.score.explanation}</p>
      </details>
    </article>
  );
}
