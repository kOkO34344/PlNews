import DeepDivePanel from "@/components/DeepDivePanel";
import StoryCard from "@/components/StoryCard";
import TrendChart from "@/components/TrendChart";
import { getLatestDigest, getTrend, type Category } from "@/lib/api";

const SECTIONS: { key: Category; label: string }[] = [
  { key: "bg_politics", label: "🇧🇬 Bulgarian politics" },
  { key: "global_politics", label: "🌍 Global politics" },
  { key: "ai_tech_business", label: "🤖 AI · tech · business" },
];

export default async function Page() {
  const [digest, trend] = await Promise.all([getLatestDigest(), getTrend()]);

  if (!digest) {
    return (
      <>
        <h1>3-3-3 Democracy-Aware News Analyst</h1>
        <p className="muted">
          No digest yet. Start the API (<code>uvicorn app.main:app</code>) and run{" "}
          <code>plnews build</code>.
        </p>
      </>
    );
  }

  const net = Number(digest.stats?.net_direction ?? 0);

  return (
    <>
      <h1>3-3-3 Digest — {digest.digest_date}</h1>
      <p className="muted small">
        {digest.stats?.fetched ?? 0} articles → {digest.stats?.clusters ?? 0} stories → {digest.items.length} selected
        {" · "}democracy net{" "}
        <strong style={{ color: net < 0 ? "var(--erosion)" : "var(--strengthen)" }}>
          {net >= 0 ? "+" : ""}{net.toFixed(2)}
        </strong>
      </p>
      {digest.editorial_note && <p>{digest.editorial_note}</p>}

      {trend?.series && <TrendChart series={trend.series} />}

      {SECTIONS.map(({ key, label }) => {
        const items = digest.items.filter((i) => i.category === key).sort((a, b) => a.rank - b.rank);
        return (
          <section key={key}>
            <h2>{label}</h2>
            {items.length === 0 && <p className="muted small">No story cleared the bar today.</p>}
            {items.map((item) => <StoryCard key={item.analysis.cluster_key} item={item} />)}
          </section>
        );
      })}

      {digest.deep_dive && (
        <section>
          <h2>Deep dive</h2>
          <DeepDivePanel dd={digest.deep_dive} />
        </section>
      )}
    </>
  );
}
