// Typed API client — mirrors CONTRACT.md v4 Section 9.1 schemas exactly.
// Backend computes; frontend renders (Section 13). JWT bearer auth.

const BASE = "http://127.0.0.1:8089/api";
const TOKEN_KEY = "cb_token";

export type Status = "healthy" | "warning" | "failed" | "offline";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function headers(): HeadersInit {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function get<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`, { headers: headers() });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function send<T>(method: string, path: string, body?: unknown): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: headers(),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function sendRaw(method: string, path: string, body?: unknown): Promise<{ ok: boolean; status: number; data: unknown }> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: headers(),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data: unknown = null;
    try { data = await res.json(); } catch { /* 204 etc. */ }
    return { ok: res.ok, status: res.status, data };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

// ---------------- auth ----------------

export interface SessionResponse {
  token: string;
  user: { id: number; email: string };
}

// ---------------- environment list / detail ----------------

export interface EnvironmentSummary {
  id: number;
  name: string;
  industry_template: string;
  created_at: string;
  node_count: number;
  nodes_degraded: number;
  last_active: string | null;
  status_summary: string;
}

export interface EnvironmentDetail {
  id: number;
  name: string;
  industry_template: string;
  nodes: EnvironmentNode[];
  edges: EnvironmentEdge[];
  sensor_bindings: SensorBinding[];
}

export interface EnvironmentNode {
  id: number;
  display_name: string;
  node_type: string;
  status: Status;
  position_x: number;
  position_y: number;
}

export interface EnvironmentEdge {
  id: number;
  source_node_id: number;
  target_node_id: number;
  relationship_type: string;
  criticality: number;
}

export interface SensorBinding {
  id: number;
  node_id: number;
  mqtt_topic: string;
  unit: string;
  warning_threshold: number | null;
  failure_threshold: number | null;
}

// ---------------- polled state payload (Section 9.1) ----------------

export interface StateBinding {
  topic: string;
  unit: string;
  warning_threshold: number | null;
  failure_threshold: number | null;
  state: Status;
  if_state: Status | null;
  if_score: number | null;
  calibrated: boolean;
  warm_up: boolean;
  samples: number;
  trend: number[];
  last_value: number | null;
  last_updated: string | null;
}

export interface StateNode {
  id: number;
  display_name: string;
  node_type: string;
  status: Status;
  current_value: number | null;
  last_updated: string | null;
  anomaly_score: number;
  warm_up: boolean;
  at_risk: boolean;
  eta_seconds: number | null;
  predicted_path: string[] | null;
  position_x: number;
  position_y: number;
  bindings: StateBinding[];
}

export interface StateEdge {
  id: number;
  source: number;
  target: number;
  relationship_type: string;
  criticality: number;
  active_cascade: boolean;
}

export interface ActiveCascade {
  origin_node_id: number;
  origin_node_name: string;
  affected_nodes: number[];
  affected_node_names: string[];
  active_edges: string[];
  method: string;
}

export interface Intervention {
  recommended_node_id: number;
  recommended_node_name: string;
  score: number;
  score_breakdown: {
    downstream_count_norm: number;
    propagation_prob: number;
    time_to_impact_inv_norm: number;
    criticality: number;
  };
  explanation: string;
  method: string;
}

export interface RankedIntervention {
  node_id: number;
  node_name: string;
  score: number;
  breakdown: {
    downstream_count_norm: number;
    propagation_prob: number;
    time_to_impact_inv_norm: number;
    criticality: number;
  };
  weights: Record<string, number>;
  eta_seconds: number;
  downstream_nodes: number[];
  downstream_node_names: string[];
  rank: number;
  label: string | null;
  method: string;
}

export interface ValidationMetrics {
  precision: number | null;
  recall: number | null;
  scope_label: string;
  warm_up: boolean;
  bindings_tracked: number;
  bindings_calibrated?: number;
  method?: string;
}

export interface BeforeAfterProjection {
  before: { downstream_systems_affected: number };
  after: { downstream_systems_affected: number };
  headline: string;
  method: string;
}

export interface EnvironmentState {
  environment_id: number;
  nodes: StateNode[];
  edges: StateEdge[];
  active_cascade: ActiveCascade | null;
  intervention: Intervention | null;
  ranked: RankedIntervention[];
  before_after: BeforeAfterProjection | null;
  validation_metrics: ValidationMetrics | null;
}

export const api = {
  // auth
  signup: (email: string, password: string) =>
    sendRaw("POST", "/auth/signup", { email, password }),
  login: (email: string, password: string) =>
    sendRaw("POST", "/auth/login", { email, password }),
  logout: () => sendRaw("POST", "/auth/logout"),

  // environments
  environments: () => get<{ environments: EnvironmentSummary[] }>("/environments"),
  createEnvironment: (name: string, industry_template: string) =>
    sendRaw("POST", "/environments", { name, industry_template }),
  environment: (id: number | string) =>
    get<EnvironmentDetail>(`/environments/${id}`),
  updateEnvironment: (id: number | string, body: { name?: string; industry_template?: string }) =>
    sendRaw("PATCH", `/environments/${id}`, body),
  deleteEnvironment: (id: number) => sendRaw("DELETE", `/environments/${id}`),

  // builder
  addNode: (envId: number | string, body: { display_name: string; node_type: string }) =>
    sendRaw("POST", `/environments/${envId}/nodes`, body),
  updateNode: (envId: number | string, nodeId: number, body: {
    display_name?: string; node_type?: string;
  }) => sendRaw("PATCH", `/environments/${envId}/nodes/${nodeId}`, body),
  deleteNode: (envId: number | string, nodeId: number) =>
    sendRaw("DELETE", `/environments/${envId}/nodes/${nodeId}`),
  deleteEdge: (envId: number | string, edgeId: number) =>
    sendRaw("DELETE", `/environments/${envId}/edges/${edgeId}`),
  deleteBinding: (envId: number | string, bindingId: number) =>
    sendRaw("DELETE", `/environments/${envId}/sensor-bindings/${bindingId}`),
  updateBinding: (envId: number | string, bindingId: number, body: {
    warning_threshold?: number | null; failure_threshold?: number | null;
  }) => sendRaw("PATCH", `/environments/${envId}/sensor-bindings/${bindingId}`, body),
  addEdge: (envId: number | string, body: {
    source: number; target: number; relationship_type: string; criticality: number;
  }) => sendRaw("POST", `/environments/${envId}/edges`, body),
  addBinding: (envId: number | string, body: {
    node_id: number; mqtt_topic: string; unit: string;
    warning_threshold?: number | null; failure_threshold?: number | null;
    baseline?: number | null;
  }) => sendRaw("POST", `/environments/${envId}/sensor-bindings`, body),

  // polled state
  state: (envId: number | string) =>
    get<EnvironmentState>(`/environments/${envId}/state`),

  // honesty labels
  methods: () => get<{ components: { name: string; method: string }[] }>("/methods"),
};

export { sendRaw };
