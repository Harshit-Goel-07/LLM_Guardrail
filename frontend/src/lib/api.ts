// Typed API client for the FastAPI guardrail backend.
// Local dev: Vite proxy forwards /api and /v1 to http://localhost:8000.
// Production: set VITE_API_BASE_URL to the backend origin.

export type Decision = "allow" | "block";

export interface HeuristicHit {
  rule_id: string;
  category: string;
  weight: number;
  description: string;
  matched_text: string;
}

export interface SemanticMatch {
  corpus_id: string;
  category: string;
  similarity: number;
  snippet: string;
}

export interface RiskBreakdown {
  heuristic_score: number;
  semantic_score: number;
  weighted_score: number;
  embedding_backend: string;
}

export interface Verdict {
  decision: Decision;
  risk_score: number;
  block_threshold: number;
  categories: string[];
  heuristic_hits: HeuristicHit[];
  semantic_matches: SemanticMatch[];
  breakdown: RiskBreakdown;
  reason: string;
  latency_ms: number;
}

export interface GuardEvent {
  id: number;
  created_at: string;
  client_id: string;
  prompt: string;
  decision: Decision;
  risk_score: number;
  block_threshold: number;
  categories: string[];
  reason: string;
  heuristic_hits: HeuristicHit[];
  semantic_matches: SemanticMatch[];
  breakdown: RiskBreakdown;
  embedding_backend: string;
  llm_provider: string | null;
  llm_model: string | null;
  llm_response: string | null;
  detection_latency_ms: number;
  flagged_false_positive: boolean;
  flagged_false_negative: boolean;
}

export interface Stats {
  total: number;
  blocked: number;
  allowed: number;
  block_rate: number;
  false_positives: number;
  false_positive_rate: number;
  avg_detection_latency_ms: number;
  avg_risk_score: number;
  category_counts: Record<string, number>;
  risk_histogram: number[];
  timeline: { hour: string; allow: number; block: number }[];
}

export interface ChatResponse {
  event_id: number;
  blocked: boolean;
  verdict: Verdict;
  response: string | null;
  provider: string | null;
  model: string | null;
}

export interface ServiceStatus {
  status: string;
  app: string;
  environment: string;
  llm_provider: string;
  llm_model: string;
  database: string;
  embedding_backend: string;
  corpus_entries: number;
  block_threshold: number;
}

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

function url(path: string): string {
  return `${BASE}${path}`;
}

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async health(): Promise<{ status: string; app: string }> {
    return j(await fetch(url("/health")));
  },
  async status(): Promise<ServiceStatus> {
    return j(await fetch(url("/v1/status")));
  },
  async chat(prompt: string, clientId = "dashboard"): Promise<ChatResponse> {
    return j(
      await fetch(url("/v1/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, client_id: clientId }),
      })
    );
  },
  async analyze(prompt: string, clientId = "dashboard"): Promise<Verdict> {
    return j(
      await fetch(url("/v1/analyze"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, client_id: clientId }),
      })
    );
  },
  async events(params: {
    limit?: number;
    offset?: number;
    decision?: Decision;
  } = {}): Promise<GuardEvent[]> {
    const q = new URLSearchParams();
    q.set("limit", String(params.limit ?? 100));
    q.set("offset", String(params.offset ?? 0));
    if (params.decision) q.set("decision", params.decision);
    return j(await fetch(url(`/api/events?${q.toString()}`)));
  },
  async stats(windowHours = 24): Promise<Stats> {
    return j(await fetch(url(`/api/stats?window_hours=${windowHours}`)));
  },
  async flag(
    id: number,
    body: { false_positive?: boolean; false_negative?: boolean }
  ): Promise<GuardEvent> {
    return j(
      await fetch(url(`/api/events/${id}/flag`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
    );
  },
};
