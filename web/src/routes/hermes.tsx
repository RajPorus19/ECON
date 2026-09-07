import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { apiGet, type Paginated } from "../lib/api";

export const Route = createFileRoute("/hermes")({
  component: HermesPage,
});

type LlmRow = {
  id: number;
  created_at: string;
  reason: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  success: boolean;
  request_text: string;
  response: Record<string, unknown>;
};

function HermesPage() {
  const query = useQuery({
    queryKey: ["llm-calls"],
    queryFn: () => apiGet<Paginated<LlmRow>>("/api/v1/llm-calls"),
  });
  const rows = query.data?.results ?? [];

  return (
    <div>
      <h1 className="text-2xl font-semibold">Hermes activity</h1>
      <p className="text-sm text-stone-500">Why the LLM was called, and what it created.</p>
      <ul className="mt-4 space-y-3">
        {rows.length === 0 ? <li className="text-stone-500">No Hermes calls yet.</li> : null}
        {rows.map((row) => (
          <li key={row.id} className="rounded-lg border border-stone-200 bg-white p-4">
            <p className="text-sm font-medium">{row.request_text || "(no request text)"}</p>
            <p className="mt-1 text-xs text-stone-500">
              {new Date(row.created_at).toLocaleString()} · {row.reason} · {row.model} ·{" "}
              {row.prompt_tokens + row.completion_tokens} tokens · {row.success ? "SUCCESS" : "FAIL"}
            </p>
            <pre className="mt-2 overflow-x-auto text-xs text-stone-600">
              {JSON.stringify(row.response, null, 2)}
            </pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
