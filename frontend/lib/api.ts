// Read per request on the server, never inlined at build time. Ports 3000 and 8000 are
// commonly taken; set API_BASE when the backend is elsewhere.
export const API_BASE = process.env.API_BASE ?? "http://localhost:8000/api";

export type Lean =
  | "left" | "center_left" | "center" | "center_right" | "right"
  | "state_aligned" | "oligarch_linked" | "unknown";

export type Category = "bg_politics" | "global_politics" | "ai_tech_business";

export interface DemocracyImpact {
  dimension: string;
  direction: number;   // -2 .. +2
  rationale: string;
  confidence: number;
}

export interface StoryAnalysis {
  cluster_key: string;
  category: Category;
  headline: string;
  what_happened: string;
  why_it_matters: string;
  claims: { text: string; status: string; evidence?: string | null }[];
  democracy: {
    relevant: boolean;
    impacts: DemocracyImpact[];
    net_direction: number;
    significance: number;
    precedent?: string | null;
    watch_next: string[];
  };
  bias: {
    coverage_spread: string;
    framing_devices: string[];
    omitted_context: string[];
    source_diversity: number;
    propaganda_markers: string[];
  };
  entities: string[];
  novelty: number;
  credibility: number;
  impact_scope: number;
  uncertainty?: string | null;
  contrarian_read?: string | null;
  tags: string[];
}

export interface ArticleRef {
  source_slug: string;
  source_name: string;
  lean: Lean;
  reliability: string;
  title: string;
  url: string;
}

export interface DigestItem {
  rank: number;
  category: Category;
  analysis: StoryAnalysis;
  score: { total: number; explanation: string };
  refs: ArticleRef[];
}

/**
 * A translated digest is the *same* structures with translated strings — a full
 * StoryAnalysis per story rather than parallel arrays of loose text, so the UI can swap
 * `item.analysis` wholesale and nothing can drift out of alignment.
 */
export interface DigestTranslation {
  editorial_note?: string | null;
  items: Record<string, StoryAnalysis>;
  deep_dive?: DeepDive | null;
}

export interface DailyDigest {
  digest_date: string;
  generated_at: string;
  items: DigestItem[];
  deep_dive: DeepDive | null;
  deep_dive_refs: ArticleRef[];
  stats: Record<string, number>;
  editorial_note?: string | null;
  translations?: Record<string, DigestTranslation> | null;
}

export interface TrendPoint {
  date: string;
  net_direction: number;
  relevant: number;
  erosion?: number;
  strengthening?: number;
}

export interface DeepDive {
  title: string;
  executive_summary: string;
  background: string;
  mechanisms: string;
  democracy_analysis: string;
  comparative_precedent: string;
  stakeholders: string[];
  scenarios: { name: string; probability: number; description: string; early_indicators: string[] }[];
  what_to_watch: string[];
  open_questions: string[];
  counterargument: string;
  confidence: number;
}

async function get<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    // The dashboard is useful even with the backend down: the caller falls back
    // to sample data and says so on the page.
    return null;
  }
}

export const getLatestDigest = () => get<DailyDigest>("/digests/latest");
export const getDigest = (d: string) => get<DailyDigest>(`/digests/${d}`);
export const getTrend = async (days = 30): Promise<TrendPoint[]> =>
  (await get<{ series: TrendPoint[] }>(`/democracy/trend?days=${days}`))?.series ?? [];
