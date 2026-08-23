import Dashboard from "@/components/Dashboard";
import { getLatestDigest, getTrend } from "@/lib/api";
import { sampleDigest, sampleTrend } from "@/lib/sample";

export const dynamic = "force-dynamic";

export default async function Page() {
  const [live, liveTrend] = await Promise.all([getLatestDigest(), getTrend()]);
  const today = new Date().toISOString().slice(0, 10);

  const digest = live ?? sampleDigest(today);
  const trend = liveTrend.length > 0 ? liveTrend : sampleTrend(digest.digest_date);

  return <Dashboard digest={digest} trend={trend} isSample={!live} />;
}
