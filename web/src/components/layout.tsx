import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

const NAV = [
  { to: "/", label: "Dashboard" },
  { to: "/requests", label: "Requests" },
  { to: "/knowledge", label: "Knowledge" },
  { to: "/flows", label: "Flows" },
  { to: "/graph", label: "Graph" },
  { to: "/hermes", label: "Hermes" },
  { to: "/optimizations", label: "Optimizations" },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[220px_1fr]">
      <aside className="border-b border-stone-300 bg-[#ebe4d6] px-4 py-5 lg:border-b-0 lg:border-r">
        <p className="font-semibold tracking-tight">ECON</p>
        <p className="mt-1 text-xs text-stone-500">Execution &amp; Cognitive Optimization</p>
        <nav className="mt-6 flex flex-col gap-1" aria-label="Main">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-md px-2 py-1.5 text-sm text-stone-800 hover:bg-white"
              activeProps={{ className: "rounded-md px-2 py-1.5 text-sm bg-white font-medium" }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <p className="mt-8 text-xs text-stone-500">
          <a className="underline" href="http://127.0.0.1:8000/admin/">
            Django Admin
          </a>
        </p>
      </aside>
      <main className="px-4 py-6 lg:px-8">{children}</main>
    </div>
  );
}
