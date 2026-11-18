"use client";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt, t } from "@/i18n";

export default function MiniPlot({ data, label }: { data: { year: number; v: number }[]; label: string }) {
  return (
    <ResponsiveContainer width="100%" height={120}>
      <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "var(--ec-text-muted)" }} stroke="var(--ec-border)" />
        <YAxis tick={{ fontSize: 10, fill: "var(--ec-text-muted)" }} stroke="var(--ec-border)" domain={["auto", "auto"]} />
        <Tooltip contentStyle={{ background: "var(--ec-surface)", border: "1px solid var(--ec-border)", color: "var(--ec-text)" }} labelFormatter={(y) => t("hud.year", { year: y })} formatter={(v) => [fmt(Number(v), 1), label]} />
        <Line type="monotone" dataKey="v" stroke="var(--ec-primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
