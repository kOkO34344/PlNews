/**
 * Sample digest for the empty state.
 *
 * The dashboard has to be legible before the first `plnews build` runs, so it falls
 * back to this and labels itself as sample data on the page. Everything here is
 * invented — the outlets are fictional and the events are illustrative. Nothing in
 * this file should ever be presented as reporting.
 */
import type { ArticleRef, DailyDigest, DigestItem, TrendPoint } from "./api";

const ref = (name: string, lean: ArticleRef["lean"], reliability = "high"): ArticleRef => ({
  source_slug: name.toLowerCase().replace(/\W+/g, "-"),
  source_name: name,
  lean,
  reliability,
  title: "Sample coverage",
  url: "https://example.org/sample",
});

type Seed = {
  key: string;
  category: DigestItem["category"];
  rank: number;
  headline: string;
  what: string;
  why: string;
  dims: { dimension: string; direction: number; rationale: string; confidence: number }[];
  significance: number;
  spread: string;
  devices: string[];
  omitted: string[];
  unknown?: string;
  counter?: string;
  claims: { text: string; status: string; evidence?: string }[];
  refs: ArticleRef[];
  score: number;
  explanation: string;
};

const SEEDS: Seed[] = [
  {
    key: "s-bg-1", category: "bg_politics", rank: 1,
    headline: "Parliament shortens the window for challenging procurement awards",
    what: "An amendment cutting the appeal window for public procurement decisions from 30 days to 10 passed second reading, 127 to 94, attached to an unrelated transport bill.",
    why: "Procurement appeals are the main route by which losing bidders expose rigged tenders. A ten-day window favours parties who knew the timetable in advance.",
    dims: [
      { dimension: "anticorruption", direction: -2, rationale: "Shortens the only practical civilian check on tender awards, with no compensating oversight added.", confidence: 0.78 },
      { dimension: "rule_of_law", direction: -1, rationale: "Passed as a rider to an unrelated bill, bypassing the responsible committee.", confidence: 0.62 },
    ],
    significance: 0.82,
    spread: "Outlets close to the coalition led on 'cutting red tape for infrastructure'; independent outlets led on the committee bypass. Neither disputes the vote count.",
    devices: ["'streamlining' used for a removal of review", "passive voice on who proposed the rider"],
    omitted: ["the pending EU funds audit covering the same tender categories"],
    unknown: "Whether the rider originated with the ministry or with individual MPs — the register does not say.",
    counter: "Appeal windows in several member states are shorter still, and the previous 30 days was routinely used to stall delivery rather than to expose fraud.",
    claims: [
      { text: "The amendment passed 127-94 on second reading.", status: "established", evidence: "Parliamentary record" },
      { text: "It was attached to a transport bill without committee review.", status: "reported", evidence: "Two outlets, one committee member on record" },
      { text: "The change was requested by a specific contractor.", status: "speculative", evidence: "Single anonymous source" },
    ],
    refs: [ref("Morning Ledger", "center"), ref("The Standard", "center_right"), ref("Kanal 4", "state_aligned", "medium"), ref("Praktika", "center_left")],
    score: 0.812,
    explanation: "democracy 0.79 · impact 0.71 · novelty 0.85 · credibility 0.88 · fit 0.50",
  },
  {
    key: "s-bg-2", category: "bg_politics", rank: 2,
    headline: "Judicial council delays prosecutor general vote for a third session",
    what: "The Supreme Judicial Council adjourned without voting on the nomination, the third consecutive session to end without a quorum on the item.",
    why: "The acting appointment has now run longer than the constitutional interim it was meant to cover.",
    dims: [
      { dimension: "checks_and_balances", direction: -1, rationale: "An indefinite acting appointment is not subject to the accountability the permanent office carries.", confidence: 0.7 },
    ],
    significance: 0.6,
    spread: "Broadly consistent factual account across the spectrum; disagreement is about who benefits from the delay.",
    devices: ["'procedural delay' framing obscures a repeated, deliberate absence"],
    omitted: ["the names of the members who did not attend"],
    unknown: "Whether a fourth session is scheduled.",
    counter: "A rushed appointment under political pressure would be worse than a delay, and members abstaining may be doing exactly what independence requires.",
    claims: [
      { text: "Three consecutive sessions ended without a vote.", status: "established" },
      { text: "The absences were coordinated.", status: "contested", evidence: "Two members deny it; one confirms a shared position" },
    ],
    refs: [ref("Morning Ledger", "center"), ref("Praktika", "center_left")],
    score: 0.664,
    explanation: "democracy 0.61 · impact 0.52 · novelty 0.40 · credibility 0.82 · fit 0.50 · −0.06 (one editorial lean)",
  },
  {
    key: "s-bg-3", category: "bg_politics", rank: 3,
    headline: "State advertising budget concentrates further in three outlets",
    what: "A transparency filing shows 61% of state institutional advertising in the last quarter went to three media groups, up from 44% a year earlier.",
    why: "State advertising is the quiet lever in a small market: it does not censor, it just makes some newsrooms solvent and others not.",
    dims: [
      { dimension: "media_freedom", direction: -1, rationale: "Concentration of state spend raises the cost of critical coverage without any formal restriction.", confidence: 0.66 },
      { dimension: "information_integrity", direction: -1, rationale: "The three recipients carry the government line more consistently than the market average.", confidence: 0.5 },
    ],
    significance: 0.55,
    spread: "Only reported by outlets that received none of the spend, which is itself part of the story.",
    devices: [],
    omitted: ["per-institution breakdown, which the filing does not require"],
    unknown: "Whether the concentration reflects reach metrics or selection.",
    claims: [{ text: "61% of quarterly state advertising went to three groups.", status: "established", evidence: "Public transparency filing" }],
    refs: [ref("Praktika", "center_left"), ref("Signal", "center", "medium")],
    score: 0.598,
    explanation: "democracy 0.58 · impact 0.44 · novelty 0.66 · credibility 0.71 · fit 0.50 · −0.08 (single source)",
  },
  {
    key: "s-gl-1", category: "global_politics", rank: 1,
    headline: "Constitutional court blocks emergency powers extension",
    what: "The court ruled 9-4 that a fourth extension of emergency powers exceeded the constitutional limit, giving the government 60 days to legislate normally or let the measures lapse.",
    why: "Emergency powers that renew indefinitely are the standard route from ordinary government to something else. A court that can still say no is the check working.",
    dims: [
      { dimension: "checks_and_balances", direction: 2, rationale: "A court constrained the executive on a question the executive had declared beyond review.", confidence: 0.85 },
      { dimension: "rule_of_law", direction: 1, rationale: "Restores the ordinary legislative route for measures that had bypassed it.", confidence: 0.72 },
    ],
    significance: 0.88,
    spread: "Government outlets emphasise the 60-day window as an endorsement of the measures; others lead on the limit.",
    devices: ["'gives the government time' reframes a deadline as a concession"],
    omitted: ["the four dissenting opinions, which are published but unreported"],
    unknown: "Whether the government will legislate or let the powers lapse.",
    counter: "A 60-day grace period is long enough to legislate the same powers permanently, which would be a worse outcome than the emergency framing.",
    claims: [
      { text: "The court ruled 9-4.", status: "established", evidence: "Published judgment" },
      { text: "The government intends to legislate rather than let the powers lapse.", status: "reported", evidence: "Spokesperson, on the record" },
    ],
    refs: [ref("Wire International", "center"), ref("The Standard", "center_right"), ref("Continental", "center_left"), ref("Evening Report", "center"), ref("Signal", "center", "medium")],
    score: 0.874,
    explanation: "democracy 0.86 · impact 0.80 · novelty 0.90 · credibility 0.92 · fit 0.50",
  },
  {
    key: "s-gl-2", category: "global_politics", rank: 2,
    headline: "Election observers report unequal ballot access in three regions",
    what: "A monitoring mission found polling station closures concentrated in three opposition-leaning regions, raising average travel distance to a ballot box by 21 km.",
    why: "Nobody has to be stopped from voting if the nearest booth is far enough away.",
    dims: [
      { dimension: "electoral_integrity", direction: -2, rationale: "Closures fall disproportionately on one side of the electorate, with no stated methodology for site selection.", confidence: 0.74 },
    ],
    significance: 0.79,
    spread: "The mission's report is quoted selectively on both sides; the 21 km figure appears only in full-text coverage.",
    devices: ["'consolidation' for closure", "regional averages that hide the concentration"],
    omitted: ["the commission's stated cost rationale"],
    unknown: "Whether the pattern predates the current commission.",
    counter: "Rural depopulation genuinely does force consolidation, and opposition-leaning regions are also the most depopulated.",
    claims: [
      { text: "Average distance to a polling station rose 21 km in the affected regions.", status: "established", evidence: "Observer mission report, table 4" },
      { text: "Site selection was politically motivated.", status: "contested" },
    ],
    refs: [ref("Wire International", "center"), ref("Continental", "center_left"), ref("Evening Report", "center")],
    score: 0.791,
    explanation: "democracy 0.80 · impact 0.68 · novelty 0.72 · credibility 0.84 · fit 0.50",
  },
  {
    key: "s-gl-3", category: "global_politics", rank: 3,
    headline: "Two governments sign a data-sharing pact with no judicial review clause",
    what: "The agreement allows direct requests between interior ministries without a court in either country reviewing the request.",
    why: "Cross-border requests that skip a judge are how domestic protections get laundered.",
    dims: [
      { dimension: "civil_liberties", direction: -1, rationale: "Removes judicial review from a class of requests that previously required it.", confidence: 0.68 },
      { dimension: "rule_of_law", direction: -1, rationale: "Signed as an executive agreement, so neither parliament votes on it.", confidence: 0.6 },
    ],
    significance: 0.64,
    spread: "Covered as a security story almost everywhere; the review clause appears in two outlets.",
    devices: ["'streamlined cooperation'"],
    omitted: ["the text of the superseded agreement, which required a warrant"],
    unknown: "Whether existing warrant requirements survive in domestic law.",
    claims: [{ text: "The pact contains no judicial review requirement.", status: "reported", evidence: "Text published by one outlet" }],
    refs: [ref("Continental", "center_left"), ref("Signal", "center", "medium")],
    score: 0.612,
    explanation: "democracy 0.63 · impact 0.55 · novelty 0.61 · credibility 0.70 · fit 0.50",
  },
  {
    key: "s-ai-1", category: "ai_tech_business", rank: 1,
    headline: "Regulator opens inquiry into recommendation ranking during an election period",
    what: "A platform regulator opened a formal inquiry into whether a recommender system down-ranked civic content in the four weeks before a national vote.",
    why: "Ranking is not censorship and is not covered by the rules written for censorship, which is exactly the gap the inquiry is testing.",
    dims: [
      { dimension: "information_integrity", direction: 1, rationale: "First use of the inquiry power against ranking rather than removal; establishes that ranking is reviewable.", confidence: 0.6 },
      { dimension: "electoral_integrity", direction: 0, rationale: "No finding yet; the effect on the vote is unmeasured and may be unmeasurable.", confidence: 0.55 },
    ],
    significance: 0.66,
    spread: "Tech press frames it as regulatory overreach; civic-tech outlets frame it as overdue. The scope of the inquiry is reported consistently.",
    devices: ["'shadowbanning' used for ordinary ranking changes"],
    omitted: ["the platform's published ranking change log for the period"],
    unknown: "Whether the regulator has access to the ranking model or only to outputs.",
    counter: "Ranking changes happen weekly for a hundred commercial reasons; finding intent here may be impossible and the inquiry may set a precedent that chills ordinary product work.",
    claims: [
      { text: "A formal inquiry was opened.", status: "established", evidence: "Regulator's published notice" },
      { text: "Civic content reach fell during the period.", status: "contested", evidence: "Two independent measurements disagree" },
    ],
    refs: [ref("Terminal", "center"), ref("The Standard", "center_right"), ref("Signal", "center", "medium")],
    score: 0.702,
    explanation: "democracy 0.65 · impact 0.72 · novelty 0.80 · credibility 0.78 · fit 0.50",
  },
  {
    key: "s-ai-2", category: "ai_tech_business", rank: 2,
    headline: "Chipmaker reports a third straight quarter of data-centre revenue above expectations",
    what: "Quarterly data-centre revenue came in 14% above guidance; the company raised its next-quarter forecast.",
    why: "Compute concentration is the substrate everything else in this category sits on.",
    dims: [],
    significance: 0,
    spread: "Numbers reported identically everywhere; the disagreement is entirely about what they imply.",
    devices: ["analyst quotes presented as findings"],
    omitted: ["customer concentration, disclosed in the filing but rarely quoted"],
    counter: undefined,
    claims: [{ text: "Data-centre revenue was 14% above guidance.", status: "established", evidence: "Company filing" }],
    refs: [ref("Terminal", "center"), ref("The Standard", "center_right")],
    score: 0.541,
    explanation: "democracy 0.00 · impact 0.78 · novelty 0.45 · credibility 0.90 · fit 0.50",
  },
  {
    key: "s-ai-3", category: "ai_tech_business", rank: 3,
    headline: "Court rules scraped archives are not covered by an existing licence",
    what: "A first-instance ruling found that a licence covering text reuse does not extend to model training, and referred the damages question to a separate hearing.",
    why: "First-instance and narrow, but it is the first ruling to separate the two uses rather than treat training as a species of reuse.",
    dims: [
      { dimension: "information_integrity", direction: 0, rationale: "Affects who can build models, not what the public can verify; the democratic stake is indirect.", confidence: 0.45 },
    ],
    significance: 0.28,
    spread: "Headlines split between 'AI training ruled illegal' and 'narrow licence ruling'. The second is accurate.",
    devices: ["a first-instance ruling reported as settled law"],
    omitted: ["that the damages question is unresolved"],
    unknown: "Whether it will be appealed. It almost certainly will be.",
    counter: "A single first-instance ruling in one jurisdiction is being read for far more than it can carry.",
    claims: [
      { text: "The court found the licence does not cover training.", status: "established", evidence: "Judgment text" },
      { text: "The ruling makes model training unlawful.", status: "speculative", evidence: "Not what the judgment says" },
    ],
    refs: [ref("Terminal", "center"), ref("Evening Report", "center"), ref("Continental", "center_left")],
    score: 0.503,
    explanation: "democracy 0.18 · impact 0.60 · novelty 0.74 · credibility 0.80 · fit 0.50 · −0.05 (flags: no_counterview)",
  },
];

function toItem(seed: Seed): DigestItem {
  const relevant = seed.dims.length > 0;
  const net = relevant
    ? Math.round(seed.dims.reduce((a, d) => a + d.direction, 0) / seed.dims.length)
    : 0;
  return {
    rank: seed.rank,
    category: seed.category,
    score: { total: seed.score, explanation: seed.explanation },
    refs: seed.refs,
    analysis: {
      cluster_key: seed.key,
      category: seed.category,
      headline: seed.headline,
      what_happened: seed.what,
      why_it_matters: seed.why,
      claims: seed.claims as never,
      democracy: {
        relevant,
        impacts: seed.dims as never,
        net_direction: net,
        significance: seed.significance,
        precedent: null,
        watch_next: relevant ? ["Follow-up filing or vote within 30 days"] : [],
      },
      bias: {
        coverage_spread: seed.spread,
        framing_devices: seed.devices,
        omitted_context: seed.omitted,
        source_diversity: Math.min(seed.refs.length / 5, 1),
        propaganda_markers: [],
      },
      entities: [],
      novelty: 0.7,
      credibility: 0.82,
      impact_scope: 0.65,
      uncertainty: seed.unknown ?? null,
      contrarian_read: seed.counter ?? null,
      tags: [],
    },
  };
}

/** A plausible 30-day trace: mostly small negative drift, one sharp recovery. */
export function sampleTrend(endDate: string, days = 30): TrendPoint[] {
  const end = new Date(endDate);
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(end);
    d.setDate(end.getDate() - (days - 1 - i));
    const wave = Math.sin(i / 3.1) * 0.22 + Math.sin(i / 7.7) * 0.3;
    const drift = -0.18 - i * 0.004;
    const spike = i === days - 6 ? 0.75 : 0;
    return {
      date: d.toISOString().slice(0, 10),
      net_direction: Number(Math.max(-1, Math.min(1, wave + drift + spike)).toFixed(2)),
      relevant: 4 + (i % 4),
    };
  });
}

export function sampleDigest(date: string): DailyDigest {
  const items = SEEDS.map(toItem);
  return {
    digest_date: date,
    generated_at: new Date().toISOString(),
    items,
    deep_dive: {
      title: "The ten-day window",
      executive_summary:
        "A procurement appeal window was cut from 30 days to 10 by an amendment attached to a transport bill. On its own it is a scheduling change. Read against the last eighteen months of procurement law, it is the fourth measure in a row to shorten, narrow or reroute the paths by which a losing bidder can force a tender into public view.",
      background:
        "The 30-day window dates from the 2007 accession-era procurement act and survived two reform waves. The first narrowing came eighteen months ago, when appeals were made to require a deposit. The second moved appeals from an independent commission to a chamber whose members the ministry nominates. This is the third.",
      mechanisms:
        "The change amends the appeals article of the procurement act. It takes effect on publication, applies to tenders already advertised, and does not alter the deposit requirement. There is no transitional provision, which means appeals already in preparation lose most of their remaining time.",
      democracy_analysis:
        "Procurement is where the money is, so procurement review is where anticorruption is either real or decorative. None of the three measures is dramatic alone; together they raise the cost and lower the odds of a challenge to the point where challenging is irrational for a firm that wants future contracts. That is the mechanism: not prohibition, but making the lawful route pointless.",
      comparative_precedent:
        "The Hungarian sequence after 2011 followed the same order — deposit, then venue, then clock — and the analogy is close on the mechanism. It breaks on the money: EU funds oversight here still has a live audit trail, and the Commission has an instrument it did not have then.",
      stakeholders: [
        "Governing coalition — needs delivery before the audit — has the votes and the clock",
        "Losing bidders — need time and standing — have neither after this",
        "European Commission — needs a defensible audit — has the funds lever",
        "Independent press — needs the appeal filings, which are the source for most tender reporting — has only publication",
      ],
      scenarios: [
        {
          name: "Quiet implementation",
          probability: 0.5,
          description: "The change takes effect, appeal volume falls by more than half within two quarters, and nothing formally happens.",
          early_indicators: ["Appeal filings drop in the first month", "No Commission letter by day 45"],
        },
        {
          name: "Commission challenge",
          probability: 0.3,
          description: "The audit flags the change as inconsistent with fund conditionality and the window is restored in part.",
          early_indicators: ["Audit scope extended", "Ministry briefing on 'clarification'"],
        },
        {
          name: "Constitutional referral",
          probability: 0.2,
          description: "The opposition secures the signatures for a referral and the court suspends the article pending review.",
          early_indicators: ["Signature count reaching the threshold within 14 days"],
        },
      ],
      what_to_watch: [
        "Appeal filing volume, published monthly",
        "Whether the transitional gap is fixed in the next omnibus",
        "The audit's treatment of tenders advertised before the change",
      ],
      open_questions: [
        "Who drafted the rider — the register does not say",
        "Whether the deposit requirement is next",
      ],
      counterargument:
        "Three measures in eighteen months is a pattern only if you assume a common author. Procurement delay is a real and expensive problem, every one of these measures has a defensible administrative rationale, and the audit trail that would expose abuse is still intact and still funded.",
      confidence: 0.58,
    },
    deep_dive_refs: SEEDS[0].refs,
    stats: {
      fetched: 422,
      clusters: 36,
      sources: 34,
      net_direction: -0.34,
      democracy_relevant: 7,
      erosion_stories: 5,
      strengthening_stories: 2,
    },
    editorial_note:
      "Two courts pushed back today and one parliament moved the other way. The through-line is procedural: nobody banned anything, they changed a deadline, a venue and a ranking.",
  };
}
