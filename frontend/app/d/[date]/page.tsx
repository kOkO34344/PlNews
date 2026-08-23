import { notFound } from "next/navigation";
import Dashboard from "@/components/Dashboard";
import { getDigest, getTrend } from "@/lib/api";
import { sampleDigest, sampleTrend } from "@/lib/sample";

export const dynamic = "force-dynamic";

export default async function ArchivedDigest({ params }: { params: Promise<{ date: string }> }) {
  const { date } = await params;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) notFound();

  const [live, liveTrend] = await Promise.all([getDigest(date), getTrend()]);
  const digest = live ?? sampleDigest(date);
  const trend = liveTrend.length > 0 ? liveTrend : sampleTrend(date);

  return <Dashboard digest={digest} trend={trend} isSample={!live} />;
}
