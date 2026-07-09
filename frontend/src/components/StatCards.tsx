import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Stats } from "@/lib/api";
import { ShieldCheck, ShieldAlert, Gauge, Timer } from "lucide-react";

interface Props {
  stats: Stats | null;
}

export function StatCards({ stats }: Props) {
  const items = [
    {
      title: "Total Requests",
      value: stats?.total ?? 0,
      icon: Gauge,
      accent: "text-primary",
    },
    {
      title: "Blocked",
      value: stats?.blocked ?? 0,
      sub: stats ? `${stats.block_rate}% block rate` : "",
      icon: ShieldAlert,
      accent: "text-destructive",
    },
    {
      title: "Allowed",
      value: stats?.allowed ?? 0,
      sub: stats ? `avg risk ${stats.avg_risk_score}` : "",
      icon: ShieldCheck,
      accent: "text-success",
    },
    {
      title: "Avg Detection Latency",
      value: stats ? `${stats.avg_detection_latency_ms} ms` : "0 ms",
      sub: stats ? `${stats.false_positive_rate}% FP rate` : "",
      icon: Timer,
      accent: "text-amber-400",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((it) => {
        const Icon = it.icon;
        return (
          <Card key={it.title}>
            <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle>{it.title}</CardTitle>
              <Icon className={`h-4 w-4 ${it.accent}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold tracking-tight">{it.value}</div>
              {it.sub ? (
                <p className="mt-1 text-xs text-muted-foreground">{it.sub}</p>
              ) : null}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
