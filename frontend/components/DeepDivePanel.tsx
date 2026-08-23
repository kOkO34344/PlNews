import type { DeepDive } from "@/lib/api";

export default function DeepDivePanel({ dd }: { dd: DeepDive }) {
  return (
    <article className="card">
      <h3>🔍 {dd.title}</h3>
      <p>{dd.executive_summary}</p>

      <h2>How we got here</h2>
      <p className="small">{dd.background}</p>

      <h2>The machinery</h2>
      <p className="small">{dd.mechanisms}</p>

      <h2>Democratic stakes</h2>
      <p className="small">{dd.democracy_analysis}</p>

      <h2>Scenarios</h2>
      <div className="grid">
        {dd.scenarios.map((s) => (
          <div key={s.name} style={{ background: "var(--panel-2)", padding: 12, borderRadius: 8 }}>
            <strong className="small">{s.name}</strong>
            <div className="meter" style={{ margin: "6px 0" }}>
              <span style={{ width: `${Math.round(s.probability * 100)}%` }} />
            </div>
            <div className="small muted">{Math.round(s.probability * 100)}%</div>
            <p className="small">{s.description}</p>
          </div>
        ))}
      </div>

      <h2>What to watch</h2>
      <ul className="small">
        {dd.what_to_watch.map((w) => <li key={w}>{w}</li>)}
      </ul>

      <div className="bias">
        <strong>Counterargument.</strong> {dd.counterargument}
      </div>
      <p className="small muted">Analysis confidence {Math.round(dd.confidence * 100)}%</p>
    </article>
  );
}
