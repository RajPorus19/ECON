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
import { apiGet } from "../lib/api";

export const Route = createFileRoute("/graph")({
  component: GraphPage,
});

type GraphPayload = {
  nodes: Array<{ id: string; type: string; label: string; confidence?: number }>;
  edges: Array<{ source: string; target: string }>;
};

function GraphPage() {
  const query = useQuery({
    queryKey: ["graph"],
    queryFn: () => apiGet<GraphPayload>("/api/v1/graph"),
  });
  const nodes: Node[] = (query.data?.nodes ?? []).map((node, index) => ({
    id: node.id,
    position: { x: (index % 5) * 180, y: Math.floor(index / 5) * 120 },
    data: { label: `${node.label}` },
    style: {
      border: "1px solid #c4b8a1",
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

  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Graph explorer</h1>
      <div className="h-[640px] overflow-hidden rounded-lg border border-stone-300 bg-white">
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <MiniMap />
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    </div>
  );
}
