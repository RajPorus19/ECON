import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiSend, type ExecuteResult } from "../lib/api";
import { formatMs } from "../lib/utils";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardTitle } from "./ui/card";

export function CommandConsole() {
  const [text, setText] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (command: string) =>
      apiSend<ExecuteResult>("/api/v1/execute?debug=true", "POST", { text: command }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["stats"] });
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
    },
  });

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const command = text.trim();
    if (!command || mutation.isPending) return;
    mutation.mutate(command);
  }

  const result = mutation.data;
  const err = mutation.error;

  return (
    <Card>
      <CardTitle>Run a command</CardTitle>
      <form className="mt-3 flex gap-2" onSubmit={submit}>
        <input
          type="text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder='Type a command, e.g. "Lance Firefox"'
          className="h-9 flex-1 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-800 outline-none focus:border-teal-700"
          disabled={mutation.isPending}
        />
        <Button type="submit" disabled={mutation.isPending || !text.trim()}>
          {mutation.isPending ? "Running…" : "Run"}
        </Button>
      </form>

      {err ? (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {err instanceof Error ? err.message : String(err)}
        </p>
      ) : null}

      {result ? (
        <div className="mt-4 space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={result.status} />
            {result.intent ? <Badge>{result.intent}</Badge> : null}
            {result.entity ? <Badge>{result.entity}</Badge> : null}
            {result.llm_used ? <Badge>LLM used</Badge> : null}
            {result.cache_layer ? <Badge>cache {result.cache_layer}</Badge> : null}
            <span className="text-xs text-stone-500">
              {formatMs(result.execution_time_ms)} · {result.tokens_saved} tokens saved
            </span>
          </div>

          {result.argv.length > 0 ? (
            <pre className="overflow-x-auto rounded-md bg-stone-900 p-3 text-xs text-stone-100">
              $ {result.argv.join(" ")}
            </pre>
          ) : null}

          {result.debug?.execution?.stdout ? (
            <pre className="overflow-x-auto rounded-md bg-stone-50 p-3 text-xs text-stone-700">
              {result.debug.execution.stdout}
            </pre>
          ) : null}
          {result.debug?.execution?.stderr ? (
            <pre className="overflow-x-auto rounded-md bg-red-50 p-3 text-xs text-red-700">
              {result.debug.execution.stderr}
            </pre>
          ) : null}

          {result.message ? (
            <p className="text-xs text-stone-500">{result.message}</p>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone: Record<string, string> = {
    success: "bg-emerald-100 text-emerald-800",
    failed: "bg-red-100 text-red-800",
    error: "bg-red-100 text-red-800",
    denied: "bg-red-100 text-red-800",
    confirm_required: "bg-amber-100 text-amber-800",
  };
  return (
    <Badge className={tone[status] ?? "bg-stone-200 text-stone-700"}>{status}</Badge>
  );
}
