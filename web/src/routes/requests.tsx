import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Badge } from "../components/ui/badge";
import { apiGet, type Paginated, type RequestRow } from "../lib/api";
import { formatMs } from "../lib/utils";

export const Route = createFileRoute("/requests")({
  component: RequestsPage,
});

const helper = createColumnHelper<RequestRow>();
const columns = [
  helper.accessor("created_at", {
    header: "Time",
    cell: (info) => new Date(info.getValue()).toLocaleTimeString(),
  }),
  helper.accessor("text", { header: "Request" }),
  helper.accessor("llm_used", {
    header: "Source",
    cell: (info) => (
      <Badge className={info.getValue() ? "bg-amber-100" : "bg-teal-100"}>
        {info.getValue() ? "Hermes" : "ECON"}
      </Badge>
    ),
  }),
  helper.accessor("status", { header: "Status" }),
  helper.accessor("duration_ms", {
    header: "Latency",
    cell: (info) => formatMs(info.getValue()),
  }),
];

function RequestsPage() {
  const query = useQuery({
    queryKey: ["requests"],
    queryFn: () => apiGet<Paginated<RequestRow>>("/api/v1/requests"),
  });
  const rows = query.data?.results ?? [];
  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel() });

  return (
    <div>
      <h1 className="text-2xl font-semibold">Requests</h1>
      <div className="mt-4 overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-100 text-stone-600">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th key={header.id} className="px-3 py-2 font-medium">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-8 text-stone-500" colSpan={5}>
                  No requests yet.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-t border-stone-200">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
