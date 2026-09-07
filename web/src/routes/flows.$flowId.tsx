import { useForm } from "@tanstack/react-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import {
  Background,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
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

function FlowEditorPage() {
  const { flowId } = Route.useParams();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["flow", flowId],
    queryFn: () => apiGet<FlowRow>(`/api/v1/flows/${flowId}`),
  });
  const flow = query.data;

  const save = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      apiSend(`/api/v1/flows/${flowId}`, "PATCH", values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["flow", flowId] }),
  });

  const form = useForm({
    defaultValues: {
      name: flow?.name ?? "",
      description: flow?.description ?? "",
      enabled: flow?.enabled ?? true,
    },
    validators: { onChange: schema },
    onSubmit: ({ value }) => save.mutateAsync(value),
  });

  if (query.isLoading) return <p>Loading flow…</p>;
  if (!flow) return <p>Flow not found.</p>;

  const nodes: Node[] = flow.nodes.map((node, index) => ({
    id: String(node.id),
    position: { x: 40, y: index * 110 },
    data: { label: `${node.node_type}: ${node.node_key}` },
  }));
  const edges: Edge[] = flow.edges.map((edge) => ({
    id: String(edge.id),
    source: String(edge.source_node),
    target: String(edge.target_node),
  }));

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
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    </div>
  );
}
