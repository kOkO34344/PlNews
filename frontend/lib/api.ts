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

export interface DailyDigest {
  digest_date: string;
  generated_at: string;
  items: DigestItem[];
  deep_dive: DeepDive | null;
  deep_dive_refs: ArticleRef[];
  stats: Record<string, number>;
  editorial_note?: string | null;
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
    const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 300 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;   // dashboard degrades to an empty state rather than a crash
  }
}

export const getLatestDigest = () => get<DailyDigest>("/digests/latest");
export const getDigest = (d: string) => get<DailyDigest>(`/digests/${d}`);
export const getTrend = () =>
  get<{ series: { date: string; net_direction: number; relevant: number }[] }>("/democracy/trend?days=30");
