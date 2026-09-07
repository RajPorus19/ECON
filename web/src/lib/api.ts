export const API_BASE =
  import.meta.env.VITE_ECON_API_URL ?? "http://127.0.0.1:8000";

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function apiSend<T>(
  path: string,
  method: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`${method} ${path} failed (${response.status})`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export type Stats = {
  requests_today: number;
  llm_calls: number;
  llm_avoidance: number;
  tokens_saved: number;
  average_latency_ms: number;
  tokens_saved_are_estimated: boolean;
};

export type RequestRow = {
  id: number;
  created_at: string;
  text: string;
  intent_name: string | null;
  llm_used: boolean;
  status: string;
  duration_ms: number;
  cache_layer: string;
  tokens_saved: number;
};

export type FlowRow = {
  id: number;
  name: string;
  description: string;
  version: number;
  confidence: number;
  usage_count: number;
  success_count: number;
  failure_count: number;
  enabled: boolean;
  intent_name: string | null;
  nodes: Array<{
    id: number;
    node_key: string;
    node_type: string;
    position: number;
    config: Record<string, unknown>;
  }>;
  edges: Array<{
    id: number;
    source_node: number;
    target_node: number;
  }>;
};

export type GraphNodeDetail = {
  id: string;
  name: string;
  type: string;
  confidence: number;
  usage: number;
  aliases: string[];
  connected_flows: string[];
  last_execution: { id: number; text: string; status: string; created_at: string | null } | null;
};
