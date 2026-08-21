import { Fragment, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type Decision, type GuardEvent } from "@/lib/api";
import { cn, formatTime, riskColor } from "@/lib/utils";
import { ChevronDown, Flag } from "lucide-react";

interface Props {
  events: GuardEvent[];
  filter: Decision | "all";
  onFilterChange: (f: Decision | "all") => void;
  onChanged: () => void;
}

export function EventsTable({ events, filter, onFilterChange, onChanged }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  async function flagFP(ev: GuardEvent) {
    await api.flag(ev.id, { false_positive: !ev.flagged_false_positive });
    onChanged();
  }

  async function flagFN(ev: GuardEvent) {
    await api.flag(ev.id, { false_negative: !ev.flagged_false_negative });
    onChanged();
  }

  const filters: (Decision | "all")[] = ["all", "block", "allow"];

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-foreground">Audit Log</CardTitle>
        <div className="flex gap-1">
          {filters.map((f) => (
            <Button
              key={f}
              size="sm"
              variant={filter === f ? "default" : "outline"}
              onClick={() => onFilterChange(f)}
            >
              {f}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Time</th>
                <th className="px-4 py-2 font-medium">Decision</th>
                <th className="px-4 py-2 font-medium">Risk</th>
                <th className="px-4 py-2 font-medium">Prompt</th>
                <th className="px-4 py-2 font-medium">Categories</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                    No events yet — send a prompt through the playground above.
                  </td>
                </tr>
              ) : (
                events.map((ev) => (
                  <Fragment key={ev.id}>
                    <tr
                      className="cursor-pointer border-b border-border/50 hover:bg-muted/30"
                      onClick={() => setExpanded(expanded === ev.id ? null : ev.id)}
                    >
                      <td className="whitespace-nowrap px-4 py-2 text-xs text-muted-foreground">
                        {formatTime(ev.created_at)}
                      </td>
                      <td className="px-4 py-2">
                        <Badge variant={ev.decision === "block" ? "destructive" : "success"}>
                          {ev.decision}
                        </Badge>
                      </td>
                      <td className={cn("px-4 py-2 font-semibold", riskColor(ev.risk_score))}>
                        {ev.risk_score}
                      </td>
                      <td className="max-w-[320px] truncate px-4 py-2">{ev.prompt}</td>
                      <td className="px-4 py-2">
                        <div className="flex flex-wrap gap-1">
                          {ev.categories.map((c) => (
                            <Badge key={c} variant="warning">
                              {c}
                            </Badge>
                          ))}
                          {ev.flagged_false_positive ? (
                            <Badge variant="outline">FP</Badge>
                          ) : null}
                          {ev.flagged_false_negative ? (
                            <Badge variant="outline">FN</Badge>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-4 py-2">
                        <ChevronDown
                          className={cn(
                            "h-4 w-4 text-muted-foreground transition-transform",
                            expanded === ev.id && "rotate-180"
                          )}
                        />
                      </td>
                    </tr>
                    {expanded === ev.id ? (
                      <tr className="border-b border-border/50 bg-background/40">
                        <td colSpan={6} className="px-4 py-3">
                          <EventDetail ev={ev} onFlagFP={() => flagFP(ev)} onFlagFN={() => flagFN(ev)} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function EventDetail({
  ev,
  onFlagFP,
  onFlagFN,
}: {
  ev: GuardEvent;
  onFlagFP: () => void;
  onFlagFN: () => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="space-y-2">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">Reason</div>
        <p className="text-sm">{ev.reason}</p>
        <div className="text-xs text-muted-foreground">
          backend: {ev.embedding_backend} · latency: {ev.detection_latency_ms}ms · score
          breakdown → heuristics {ev.breakdown.heuristic_score}, semantic{" "}
          {ev.breakdown.semantic_score}, weighted {ev.breakdown.weighted_score}
        </div>

        <div className="text-xs uppercase tracking-wide text-muted-foreground">
          Heuristic hits
        </div>
        {ev.heuristic_hits.length === 0 ? (
          <div className="text-sm text-muted-foreground">None</div>
        ) : (
          <ul className="space-y-1">
            {ev.heuristic_hits.map((h, i) => (
              <li key={i} className="rounded-md bg-muted/40 p-2 text-xs">
                <span className="font-mono text-primary">{h.rule_id}</span>{" "}
                <span className="text-muted-foreground">({h.category}, w={h.weight})</span>
                <div>{h.description}</div>
                <div className="mt-1 font-mono text-amber-400">“{h.matched_text}”</div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">
          Nearest known attacks (semantic)
        </div>
        <ul className="space-y-1">
          {ev.semantic_matches.slice(0, 3).map((m, i) => (
            <li key={i} className="rounded-md bg-muted/40 p-2 text-xs">
              <span className="font-mono text-primary">{m.corpus_id}</span>{" "}
              <span className="text-muted-foreground">({m.category})</span>{" "}
              <span className="text-cyan-300">sim={m.similarity}</span>
              <div className="mt-1 text-muted-foreground">{m.snippet}</div>
            </li>
          ))}
        </ul>

        {ev.llm_response ? (
          <>
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              LLM response ({ev.llm_provider}/{ev.llm_model})
            </div>
            <div className="rounded-md bg-muted/40 p-2 text-sm">{ev.llm_response}</div>
          </>
        ) : (
          <div className="text-xs italic text-muted-foreground">
            LLM not called (blocked at guardrail).
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={onFlagFP}>
            <Flag className="h-3.5 w-3.5" />
            {ev.flagged_false_positive ? "Unflag false positive" : "Mark false positive"}
          </Button>
          <Button size="sm" variant="outline" onClick={onFlagFN}>
            <Flag className="h-3.5 w-3.5" />
            {ev.flagged_false_negative ? "Unflag false negative" : "Mark false negative"}
          </Button>
        </div>
      </div>
    </div>
  );
}
