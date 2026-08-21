import { useCallback, useEffect, useState } from "react";
import { StatCards } from "@/components/StatCards";
import { Charts } from "@/components/Charts";
import { EventsTable } from "@/components/EventsTable";
import { Playground } from "@/components/Playground";
import { Badge } from "@/components/ui/badge";
import { api, type Decision, type GuardEvent, type ServiceStatus, type Stats } from "@/lib/api";
import { ShieldCheck, RefreshCw } from "lucide-react";

const WINDOW_OPTIONS = [1, 6, 24, 72, 168];

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [events, setEvents] = useState<GuardEvent[]>([]);
  const [status, setStatus] = useState<ServiceStatus | null>(null);
  const [filter, setFilter] = useState<Decision | "all">("all");
  const [windowHours, setWindowHours] = useState(24);
  const [online, setOnline] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, e, st] = await Promise.all([
        api.stats(windowHours),
        api.events({ limit: 200, decision: filter === "all" ? undefined : filter }),
        api.status(),
      ]);
      setStats(s);
      setEvents(e);
      setStatus(st);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, [filter, windowHours]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15">
            <ShieldCheck className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">LLM Guardrail</h1>
            <p className="text-xs text-muted-foreground">
              Prompt-injection &amp; jailbreak detection firewall · OWASP LLM01
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status ? (
            <Badge variant="outline">
              {status.llm_provider}/{status.embedding_backend} · {status.database}
            </Badge>
          ) : null}
          <Badge variant={online ? "success" : online === false ? "destructive" : "outline"}>
            {online ? "backend online" : online === false ? "backend offline" : "connecting…"}
          </Badge>
          <select
            value={windowHours}
            onChange={(e) => setWindowHours(Number(e.target.value))}
            className="rounded-md border border-border bg-background px-2 py-1 text-xs text-muted-foreground"
          >
            {WINDOW_OPTIONS.map((h) => (
              <option key={h} value={h}>
                stats: {h}h
              </option>
            ))}
          </select>
          <button
            onClick={refresh}
            className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
          >
            <RefreshCw className="h-3.5 w-3.5" /> refresh
          </button>
        </div>
      </header>

      <div className="space-y-6">
        <StatCards stats={stats} />
        <Playground onSent={refresh} />
        <Charts stats={stats} />
        <EventsTable
          events={events}
          filter={filter}
          onFilterChange={setFilter}
          onChanged={refresh}
        />
      </div>

      <footer className="mt-10 border-t border-border pt-4 text-center text-xs text-muted-foreground">
        LLM: {status?.llm_provider ?? "—"} · Embeddings: {status?.embedding_backend ?? "—"} ·
        Corpus: {status?.corpus_entries ?? "—"} entries · Data auto-refreshes every 5s
      </footer>
    </div>
  );
}
