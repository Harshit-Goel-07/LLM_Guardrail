import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Stats } from "@/lib/api";

const CATEGORY_COLORS: Record<string, string> = {
  prompt_injection: "#f43f5e",
  jailbreak: "#fb923c",
  system_prompt_leak: "#a78bfa",
  data_exfiltration: "#22d3ee",
  obfuscation: "#facc15",
  pii: "#f472b6",
  benign: "#4ade80",
};

const tooltipStyle = {
  backgroundColor: "hsl(222 45% 8%)",
  border: "1px solid hsl(217 33% 18%)",
  borderRadius: 8,
  color: "#e2e8f0",
  fontSize: 12,
};

export function Charts({ stats }: { stats: Stats | null }) {
  const histogram = (stats?.risk_histogram ?? []).map((count, i) => ({
    bucket: `${i * 10}-${i * 10 + 9}`,
    count,
    high: i >= 7,
  }));

  const categories = Object.entries(stats?.category_counts ?? {}).map(
    ([name, value]) => ({ name, value })
  );

  const timeline = stats?.timeline ?? [];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Risk Score Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={histogram}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 18%)" />
              <XAxis dataKey="bucket" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(217 33% 15%)" }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {histogram.map((d, i) => (
                  <Cell key={i} fill={d.high ? "#f43f5e" : "#22d3ee"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Attack Categories</CardTitle>
        </CardHeader>
        <CardContent>
          {categories.length === 0 ? (
            <div className="flex h-[240px] items-center justify-center text-sm text-muted-foreground">
              No categorized events yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={categories}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={2}
                >
                  {categories.map((c, i) => (
                    <Cell key={i} fill={CATEGORY_COLORS[c.name] ?? "#94a3b8"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="lg:col-span-3">
        <CardHeader>
          <CardTitle>Requests Over Time (allow vs block)</CardTitle>
        </CardHeader>
        <CardContent>
          {timeline.length === 0 ? (
            <div className="flex h-[220px] items-center justify-center text-sm text-muted-foreground">
              No time-series data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 18%)" />
                <XAxis dataKey="hour" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="allow" stroke="#4ade80" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="block" stroke="#f43f5e" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
