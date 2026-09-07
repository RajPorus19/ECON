import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { apiGet, type FlowRow, type Paginated } from "../lib/api";

export const Route = createFileRoute("/flows")({
  component: FlowsPage,
});

function FlowsPage() {
  const query = useQuery({
    queryKey: ["flows"],
    queryFn: () => apiGet<Paginated<FlowRow>>("/api/v1/flows"),
  });
  const rows = query.data?.results ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Flows</h1>
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-100">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Version</th>
              <th className="px-3 py-2">Intent</th>
              <th className="px-3 py-2">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-8 text-stone-500" colSpan={4}>
                  No flows yet.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-t border-stone-200">
                  <td className="px-3 py-2">
                    <Link className="underline" to="/flows/$flowId" params={{ flowId: String(row.id) }}>
                      {row.name}
                    </Link>
                  </td>
                  <td className="px-3 py-2">v{row.version}</td>
                  <td className="px-3 py-2">{row.intent_name ?? "—"}</td>
                  <td className="px-3 py-2">{row.confidence.toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
