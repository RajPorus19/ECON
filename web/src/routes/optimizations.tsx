import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { apiGet } from "../lib/api";
import { formatPct } from "../lib/utils";

export const Route = createFileRoute("/optimizations")({
  component: OptimizationsPage,
});

function OptimizationsPage() {
  const query = useQuery({
    queryKey: ["optimizations"],
    queryFn: () =>
      apiGet<{ intents: Array<{ intent: string; total: number; llm_calls: number; llm_avoidance: number }> }>(
        "/api/v1/optimizations",
      ),
  });
  const rows = query.data?.intents ?? [];

  return (
    <div>
      <h1 className="text-2xl font-semibold">Optimizations</h1>
      <p className="text-sm text-stone-500">LLM avoidance by intent.</p>
      <table className="mt-4 w-full text-left text-sm">
        <thead>
          <tr className="text-stone-500">
            <th className="py-2">Intent</th>
            <th>Total</th>
            <th>LLM calls</th>
            <th>Avoidance</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td className="py-8 text-stone-500" colSpan={4}>
                No intent data yet.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={row.intent} className="border-t border-stone-200">
                <td className="py-2">{row.intent}</td>
                <td>{row.total}</td>
                <td>{row.llm_calls}</td>
                <td>{formatPct(row.llm_avoidance)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
