// Typed API client — mirrors CONTRACT.md Section 7 schemas exactly.
// Backend computes; frontend renders (Section 13).

// Dev runs on :8001 — port 8000 is taken by another local process.
const BASE = "http://127.0.0.1:8089/api";

export type Status = "healthy" | "warning" | "failed" | "offline";

export interface GraphNode {
  id: string;
  display_name: string;
  status: Status;
  border_style: "solid" | "dashed" | "thick" | "dotted";
  anomaly_score?: number;
  at_risk?: boolean;
  predicted?: boolean;
  eta_seconds?: number | null;
}

export interface GraphEdge {
  from: string;
  to: string;
  criticality: number;
  active_cascade: boolean;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
  synthetic: boolean;
  replay_running: boolean;
}

export interface SensorPayload {
  node_id: string;
  tags: Record<string, { value: number | null; trend: number[]; unit: string }>;
  timestamp: string | null;
}

export interface ReplayState {
  running: boolean;
  position: number;
  total_rows: number;
  timestamp: string;
  multiplier: number;
  finished: boolean;
  locked_start: string;
  locked_multiplier: number;
}

export interface AnomalyNode {
  node_id: string;
  anomaly_score: number;
  state: Status;
  if_score: number;
  if_state: string;
  threshold_warning: number;
  threshold_failure: number;
  method: string;
  if_method: string;
}

export interface CascadePayload {
  active_edges: string[];
  synthetic: boolean;
  method: string;
  note: string | null;
}

export interface RankedIntervention {
  node_id: string;
  display_name: string;
  score: number;
  breakdown: {
    downstream_count_norm: number;
    propagation_prob: number;
    time_to_impact_inv_norm: number;
    criticality: number;
  };
  weights: Record<string, number>;
  eta_seconds: number;
  downstream_nodes: string[];
  rank: number;
  label: string | null;
  method: string;
}

export interface ExplanationPayload {
  node_id: string;
  display_name: string;
  role: string;
  score: number;
  rank: number | null;
  label: string | null;
  factors: { factor: string; label: string; weight: number; value: number; contribution: number }[];
  summary: string;
  method: string;
  honesty_labels: string[];
}

export interface BeforeAfterPayload {
  before: { downstream_systems_affected: number };
  after: { downstream_systems_affected: number };
  headline: string;
  intervention_applied: string | null;
  focus_node: string | null;
  method: string;
}

export interface ValidationPayload {
  scope: string;
  precision: number;
  recall: number;
  tp: number | null;
  fp: number | null;
  fn: number | null;
  truth_interval: string[] | null;
  truth_basis: string | null;
  method: string;
  full_dataset_available: boolean;
  full_dataset_note: string | null;
}

async function get<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function post<T>(path: string, body?: unknown): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export const api = {
  graph: () => get<GraphPayload>("/graph"),
  sensors: (nodeId: string) => get<SensorPayload>(`/sensors/${nodeId}`),
  replayState: () => get<ReplayState>("/replay/state"),
  replayStart: (multiplier?: number) =>
    post<ReplayState>("/replay/start", multiplier ? { multiplier } : {}),
  replayStop: () => post<ReplayState>("/replay/stop"),
  replayReset: () => post<ReplayState>("/replay/reset"),
  simulateFailure: () => post<{ simulated: boolean }>("/failure/simulate"),
  anomalyStatus: () => get<{ nodes: AnomalyNode[]; timestamp: string }>("/anomaly/status"),
  cascade: () => get<CascadePayload>("/cascade"),
  ranking: () => get<{ ranked: RankedIntervention[]; note: string | null }>("/intervention/ranking"),
  applyIntervention: (nodeId: string) =>
    post<{ applied: string }>("/intervention/apply", { node_id: nodeId }),
  beforeAfter: () => get<BeforeAfterPayload>("/impact/before-after"),
  validation: () => get<ValidationPayload>("/validation/metrics"),
  fullValidation: () => get<Record<string, unknown>>("/validation/full"),
  explanation: (nodeId: string) => get<ExplanationPayload>(`/explanation/${nodeId}`),
  methods: () => get<{ components: { name: string; method: string }[] }>("/methods"),
};
