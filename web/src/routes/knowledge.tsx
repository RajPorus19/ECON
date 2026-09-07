import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { apiGet, type Paginated } from "../lib/api";

export const Route = createFileRoute("/knowledge")({
  component: KnowledgePage,
});

const TABS = ["intents", "entities", "aliases", "providers", "actions", "flows"] as const;

function KnowledgePage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("intents");
  const query = useQuery({
    queryKey: ["knowledge", tab],
    queryFn: () => apiGet<Paginated<Record<string, unknown>>>(`/api/v1/${tab}`),
  });
  const rows = query.data?.results ?? [];

  return (
    <div>
      <h1 className="text-2xl font-semibold">Knowledge</h1>
      <div className="mt-4 flex flex-wrap gap-2" role="tablist">
        {TABS.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={tab === item}
            className={`rounded-md px-3 py-1.5 text-sm ${tab === item ? "bg-teal-800 text-white" : "bg-white border border-stone-300"}`}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="mt-4 overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-100">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Meta</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-8 text-stone-500" colSpan={2}>
                  Empty.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={String(row.id)} className="border-t border-stone-200">
                  <td className="px-3 py-2">
                    {tab === "flows" ? (
                      <Link className="underline" to="/flows/$flowId" params={{ flowId: String(row.id) }}>
                        {String(row.name)}
                      </Link>
                    ) : (
                      String(row.name ?? row.alias ?? row.phrase)
                    )}
                  </td>
                  <td className="px-3 py-2 text-stone-500">
                    {row.confidence !== undefined ? `conf ${row.confidence}` : ""}{" "}
                    {row.usage_count !== undefined ? `use ${row.usage_count}` : ""}
                    {row.version !== undefined ? ` v${row.version}` : ""}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
