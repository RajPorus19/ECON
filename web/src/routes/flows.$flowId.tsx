import { useForm } from "@tanstack/react-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  Background,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect } from "react";
import { z } from "zod";
import { Button } from "../components/ui/button";
import { apiGet, apiSend, type FlowRow } from "../lib/api";

export const Route = createFileRoute("/flows/$flowId")({
  component: FlowEditorPage,
});

const schema = z.object({
  name: z.string().min(1),
  description: z.string(),
  enabled: z.boolean(),
});

function flowToGraph(flow: FlowRow): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = flow.nodes.map((node, index) => {
    const ui = node.config?.ui as { x?: number; y?: number } | undefined;
    return {
      id: String(node.id),
      position: { x: ui?.x ?? 40, y: ui?.y ?? index * 110 },
      data: { label: `${node.node_type}: ${node.node_key}`, node_key: node.node_key, node_type: node.node_type },
    };
  });
  const edges: Edge[] = flow.edges.map((edge) => ({
    id: String(edge.id),
    source: String(edge.source_node),
    target: String(edge.target_node),
  }));
  return { nodes, edges };
}

function FlowEditorPage() {
  const { flowId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["flow", flowId],
    queryFn: () => apiGet<FlowRow>(`/api/v1/flows/${flowId}`),
  });
  const flow = query.data;
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const form = useForm({
    defaultValues: {
      name: "",
      description: "",
      enabled: true,
    },
    validators: { onChange: schema },
    onSubmit: ({ value }) => saveMeta.mutateAsync(value),
  });

  useEffect(() => {
    if (!flow) return;
    form.reset({
      name: flow.name,
      description: flow.description ?? "",
      enabled: flow.enabled,
    });
    const graph = flowToGraph(flow);
    setNodes(graph.nodes);
    setEdges(graph.edges);
  }, [flow, form, setEdges, setNodes]);

  const saveMeta = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      apiSend(`/api/v1/flows/${flowId}`, "PATCH", values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["flow", flowId] }),
  });

  const saveGraph = useMutation({
    mutationFn: () =>
      apiSend<FlowRow>(`/api/v1/flows/${flowId}`, "PATCH", {
        name: form.state.values.name || flow?.name,
        description: form.state.values.description ?? flow?.description,
        enabled: form.state.values.enabled,
        nodes: nodes.map((node, index) => {
          const original = flow?.nodes.find((item) => String(item.id) === node.id);
          return {
            id: Number(node.id),
            node_key: (node.data as { node_key?: string }).node_key ?? original?.node_key ?? node.id,
            node_type: (node.data as { node_type?: string }).node_type ?? original?.node_type ?? "action",
            position: index,
            x: node.position.x,
            y: node.position.y,
            config: original?.config ?? {},
          };
        }),
        edges: edges.map((edge) => ({
          source: edge.source,
          target: edge.target,
        })),
      }),
    onSuccess: (updated) => {
      if (updated && String(updated.id) !== flowId) {
        void navigate({ to: "/flows/$flowId", params: { flowId: String(updated.id) } });
        return;
      }
      void queryClient.invalidateQueries({ queryKey: ["flow", flowId] });
    },
  });

  if (query.isLoading) return <p>Loading flow…</p>;
  if (!flow) return <p>Flow not found.</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Flow editor</h1>
      <p className="text-sm text-stone-500">
        Version {flow.version} · confidence {flow.confidence.toFixed(2)} · {flow.success_count}/
        {flow.usage_count} success
      </p>
      <form
        className="grid gap-3 md:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          void form.handleSubmit();
        }}
      >
        <form.Field name="name">
          {(field) => (
            <label className="text-sm">
              Name
              <input
                className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1"
                value={field.state.value}
                onChange={(event) => field.handleChange(event.target.value)}
              />
            </label>
          )}
        </form.Field>
        <form.Field name="description">
          {(field) => (
            <label className="text-sm md:col-span-2">
              Description
              <input
                className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1"
                value={field.state.value}
                onChange={(event) => field.handleChange(event.target.value)}
              />
            </label>
          )}
        </form.Field>
        <div className="flex flex-wrap gap-2">
          <Button type="submit">Save metadata</Button>
          <Button type="button" variant="outline" onClick={() => saveGraph.mutate()}>
            Save graph (new version)
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => apiSend(`/api/v1/flows/${flowId}/disable`, "POST").then(() => query.refetch())}
          >
            Disable
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => apiSend(`/api/v1/flows/${flowId}/version`, "POST").then(() => query.refetch())}
          >
            New version
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => apiSend(`/api/v1/flows/${flowId}/test`, "POST").then((result) => alert(JSON.stringify(result)))}
          >
            Test
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={() => apiSend(`/api/v1/flows/${flowId}`, "DELETE").then(() => history.back())}
          >
            Delete
          </Button>
        </div>
      </form>
      <div className="h-[420px] rounded-lg border border-stone-300 bg-white">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    </div>
  );
}
