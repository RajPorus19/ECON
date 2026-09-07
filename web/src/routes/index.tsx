import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, CardTitle } from "../components/ui/card";
import { API_BASE, apiGet, type Stats } from "../lib/api";
import { formatMs, formatPct } from "../lib/utils";

export const Route = createFileRoute("/")({
  component: DashboardPage,
});

function DashboardPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => apiGet<Stats>("/api/v1/stats") });
  const [events, setEvents] = useState<string[]>([]);

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/api/v1/events`);
    source.onmessage = (message) => {
      setEvents((current) => [message.data, ...current].slice(0, 8));
    };
    return () => source.close();
  }, []);

  const data = stats.data;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-stone-500">Live matching and estimated LLM avoidance.</p>
      </div>
      {stats.isError ? (
        <p role="alert">Could not reach the API at {API_BASE}.</p>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Requests today" value={data?.requests_today ?? "—"} />
        <Metric label="LLM calls" value={data?.llm_calls ?? "—"} />
        <Metric
          label="LLM avoidance"
          value={data ? formatPct(data.llm_avoidance) : "—"}
        />
        <Metric
          label="Tokens saved (estimated)"
          value={data?.tokens_saved ?? "—"}
        />
        <Metric
          label="Average latency"
          value={data ? formatMs(data.average_latency_ms) : "—"}
        />
      </div>
      <Card>
        <CardTitle>Live execution</CardTitle>
        <ul className="mt-3 space-y-1 font-mono text-xs text-stone-600">
          {events.length === 0 ? <li>Waiting for events…</li> : null}
          {events.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardTitle>{label}</CardTitle>
      <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
    </Card>
  );
}
