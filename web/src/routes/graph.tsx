import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useState } from "react";
import { apiGet, type GraphNodeDetail } from "../lib/api";

export const Route = createFileRoute("/graph")({
  component: GraphPage,
});

type GraphPayload = {
  nodes: Array<{
    id: string;
    type: string;
    label: string;
    confidence?: number;
    usage?: number;
    aliases?: string[];
    connected_flows?: string[];
    last_execution?: GraphNodeDetail["last_execution"];
  }>;
  edges: Array<{ source: string; target: string }>;
};

function GraphPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["graph"],
    queryFn: () => apiGet<GraphPayload>("/api/v1/graph"),
  });
  const detail = useQuery({
    queryKey: ["graph-detail", selectedId],
    queryFn: () => apiGet<GraphNodeDetail>(`/api/v1/graph/detail?id=${encodeURIComponent(selectedId ?? "")}`),
    enabled: Boolean(selectedId),
  });
  const nodes: Node[] = (query.data?.nodes ?? []).map((node, index) => ({
    id: node.id,
    position: { x: (index % 5) * 180, y: Math.floor(index / 5) * 120 },
    data: { label: `${node.label}` },
    style: {
      border: selectedId === node.id ? "2px solid #0f766e" : "1px solid #c4b8a1",
      background: "#fffdf8",
      fontSize: 12,
      width: 160,
    },
  }));
  const edges: Edge[] = (query.data?.edges ?? []).map((edge, index) => ({
    id: `${edge.source}-${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
  }));

  const panel = detail.data;

  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Graph explorer</h1>
      <div className="grid gap-3 lg:grid-cols-[1fr_280px]">
        <div className="h-[640px] overflow-hidden rounded-lg border border-stone-300 bg-white">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            onNodeClick={(_, node) => setSelectedId(node.id)}
          >
            <MiniMap />
            <Controls />
            <Background />
          </ReactFlow>
        </div>
        <aside className="rounded-lg border border-stone-300 bg-white p-4 text-sm">
          {panel ? (
            <div className="space-y-2">
              <h2 className="text-lg font-medium">{panel.name}</h2>
              <p>Type: {panel.type}</p>
              <p>Confidence: {panel.confidence.toFixed(2)}</p>
              <p>Usage: {panel.usage}</p>
              <p>Aliases: {panel.aliases.length ? panel.aliases.join(", ") : "none"}</p>
              <p>Flows: {panel.connected_flows.length ? panel.connected_flows.join(", ") : "none"}</p>
              <p>
                Last execution:{" "}
                {panel.last_execution
                  ? `${panel.last_execution.status} — ${panel.last_execution.text}`
                  : "none"}
              </p>
            </div>
          ) : (
            <p className="text-stone-500">Click a node for details.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
