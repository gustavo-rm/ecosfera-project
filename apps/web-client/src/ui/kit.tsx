"use client";
import Link from "next/link";
import { useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import { create } from "zustand";
import { t } from "@/i18n";
import { useSettings } from "@/store/settingsStore";
import { Icon } from "./icons";

type Variant = "default" | "primary" | "ghost" | "danger";
const cls = (...c: (string | false | undefined | null)[]) => c.filter(Boolean).join(" ");

export function Button({ variant = "default", icon, large, iconOnly, children, className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: string; large?: boolean; iconOnly?: boolean }) {
  return (
    <button type="button" {...rest} className={cls("ec-btn", variant !== "default" && `ec-btn--${variant}`, large && "ec-btn--lg", iconOnly && "ec-btn--icon", className)}>
      {icon && <Icon name={icon} />}{iconOnly ? <span className="ec-sr-only">{children}</span> : children}
    </button>
  );
}
export function LinkButton({ href, variant = "default", icon, children, className, current }: { href: string; variant?: Variant; icon?: string; children: ReactNode; className?: string; current?: boolean }) {
  return <Link href={href} aria-current={current ? "page" : undefined} className={cls("ec-btn", variant !== "default" && `ec-btn--${variant}`, className)}>{icon && <Icon name={icon} />}{children}</Link>;
}

export function Panel({ title, icon, actions, children, className, as: Tag = "section", headingLevel = 2 }: { title?: string; icon?: string; actions?: ReactNode; children: ReactNode; className?: string; as?: "section" | "aside" | "div" | "nav"; headingLevel?: 2 | 3 }) {
  const id = useId(), H = `h${headingLevel}` as "h2";
  return (
    <Tag className={cls("ec-panel p-3", className)} aria-labelledby={title ? id : undefined}>
      {title && (
        <div className="mb-2 flex items-center justify-between gap-2">
          <H id={id} className="flex items-center gap-2 !text-[length:var(--ec-text-md)]">{icon && <Icon name={icon} />}{title}</H>
          {actions}
        </div>
      )}
      {children}
    </Tag>
  );
}

export interface TabDef { id: string; label: string; icon?: string }
/** Tabs with roving tabindex: Left/Right/Home/End move, as the WAI-ARIA pattern asks. */
export function Tabs({ tabs, value, onChange, label, className }: { tabs: TabDef[]; value: string; onChange: (id: string) => void; label: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const move = (delta: number | "home" | "end") => {
    const i = tabs.findIndex((x) => x.id === value);
    const n = delta === "home" ? 0 : delta === "end" ? tabs.length - 1 : (i + delta + tabs.length) % tabs.length;
    onChange(tabs[n].id);
    requestAnimationFrame(() => ref.current?.querySelector<HTMLButtonElement>(`[data-tab="${tabs[n].id}"]`)?.focus());
  };
  return (
    <div ref={ref} role="tablist" aria-label={label} className={cls("flex flex-wrap gap-1", className)}
      onKeyDown={(e) => { if (e.key === "ArrowRight") move(1); else if (e.key === "ArrowLeft") move(-1); else if (e.key === "Home") move("home"); else if (e.key === "End") move("end"); else return; e.preventDefault(); }}>
      {tabs.map((tab) => (
        <button key={tab.id} type="button" role="tab" data-tab={tab.id} aria-selected={tab.id === value} tabIndex={tab.id === value ? 0 : -1} className="ec-btn" onClick={() => onChange(tab.id)}>
          {tab.icon && <Icon name={tab.icon} />}{tab.label}
        </button>
      ))}
    </div>
  );
}

/** Modal dialog on the native <dialog>: focus trap, Esc to close and focus return come from the platform. */
export function Dialog({ open, onClose, title, children, footer, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null), id = useId();
  useEffect(() => { const d = ref.current; if (!d) return; if (open && !d.open) d.showModal(); if (!open && d.open) d.close(); }, [open]);
  return (
    <dialog ref={ref} className="ec-dialog" aria-labelledby={id} onClose={onClose} onClick={(e) => { if (e.target === ref.current) onClose(); }} style={wide ? { maxWidth: "min(1040px, calc(100vw - 24px))", width: "100%" } : { width: "100%" }}>
      {open && (
        <div className="flex max-h-[calc(100dvh-24px)] flex-col">
          <header className="flex items-center justify-between gap-3 border-b border-ec-border-subtle p-4">
            <h2 id={id}>{title}</h2>
            <Button variant="ghost" iconOnly icon="close" onClick={onClose}>{t("common.close")}</Button>
          </header>
          <div className="ec-scroll p-4">{children}</div>
          {footer && <footer className="flex flex-wrap justify-end gap-2 border-t border-ec-border-subtle p-4">{footer}</footer>}
        </div>
      )}
    </dialog>
  );
}

export function Slider({ label, value, min, max, step, onChange, format, log, hint }: { label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; format?: (v: number) => string; log?: boolean; hint?: string }) {
  const id = useId();
  // Logarithmic levers (mass, CO2...) map the track position to the exponent.
  const lo = log ? Math.log10(Math.max(min, 1e-9)) : min, hi = log ? Math.log10(max) : max;
  const pos = log ? Math.log10(Math.max(value, 1e-9)) : value;
  const shown = format ? format(value) : String(value);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="ec-label !mb-0">{label}</label>
        <output htmlFor={id} className="ec-num text-[length:var(--ec-text-sm)]">{shown}</output>
      </div>
      <input id={id} type="range" className="ec-range" min={lo} max={hi} step={log ? (hi - lo) / 200 : step} value={pos} aria-valuetext={shown}
        onChange={(e) => { const v = Number(e.target.value); onChange(log ? Math.pow(10, v) : v); }} />
      {hint && <p className="ec-muted text-[length:var(--ec-text-xs)]">{hint}</p>}
    </div>
  );
}

export function Toggle({ label, checked, onChange, icon }: { label: string; checked: boolean; onChange: (v: boolean) => void; icon?: string }) {
  return (
    <button type="button" role="switch" aria-checked={checked} className="ec-btn w-full !justify-between" onClick={() => onChange(!checked)}>
      <span className="flex items-center gap-2">{icon && <Icon name={icon} />}{label}</span>
      <span aria-hidden="true" className="ec-chip" style={checked ? { borderColor: "var(--ec-primary)", color: "var(--ec-primary)" } : undefined}>{checked ? t("common.on") : t("common.off")}</span>
    </button>
  );
}

export function Select<T extends string>({ label, value, options, onChange, hideLabel }: { label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; hideLabel?: boolean }) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className={hideLabel ? "ec-sr-only" : "ec-label"}>{label}</label>
      <select id={id} className="ec-select" value={value} onChange={(e) => onChange(e.target.value as T)}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

export function Meter({ value, label, valueText }: { value: number; label: string; valueText?: string }) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  return <div className="ec-meter" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-valuetext={valueText ?? `${pct}%`}><span style={{ width: `${pct}%` }} /></div>;
}

/** Trend with shape and text, never color alone (RNF-015). */
export function Trend({ delta, threshold = 0.01 }: { delta: number; threshold?: number }) {
  const dir = delta > threshold ? "up" : delta < -threshold ? "down" : "flat";
  return <span title={t(`trend.${dir}`)} className="inline-flex items-center"><Icon name={dir} size={16} /><span className="ec-sr-only">{t(`trend.${dir}`)}</span></span>;
}

export function Loading({ label }: { label?: string }) {
  return <div role="status" className="flex flex-col items-center justify-center gap-3 p-8 text-center"><div className="ec-pulse h-10 w-10 rounded-full border-4 border-ec-border border-t-ec-primary" aria-hidden="true" /><p>{label ?? t("state.loading")}</p></div>;
}
export function Empty({ title, hint, icon = "info", action }: { title: string; hint?: string; icon?: string; action?: ReactNode }) {
  return <div className="flex flex-col items-center justify-center gap-2 p-6 text-center"><Icon name={icon} size={32} className="ec-muted" /><p className="font-semibold">{title}</p>{hint && <p className="ec-muted max-w-prose text-[length:var(--ec-text-sm)]">{hint}</p>}{action}</div>;
}
export function ErrorState({ detail, onRetry }: { detail?: string | null; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center gap-2 p-6 text-center">
      <Icon name="alert" size={32} style={{ color: "var(--ec-danger)" }} /><p className="font-semibold">{t("state.errorTitle")}</p>
      <p className="ec-muted max-w-prose text-[length:var(--ec-text-sm)]">{t("state.errorHint")}</p>
      {detail && <code className="ec-kbd">{detail}</code>}
      {onRetry && <Button icon="reset" onClick={onRetry}>{t("common.retry")}</Button>}
    </div>
  );
}

/** Marks pedagogical text as a placeholder awaiting review by the domain authority and the pedagogical team. */
export function Ped({ k, params, as: Tag = "span", className }: { k: string; params?: Record<string, string | number>; as?: "span" | "p" | "li"; className?: string }) {
  const dev = useSettings((s) => s.devMode);
  return <Tag className={cls(dev && "ec-ped", className)} title={dev ? t("common.placeholderText") : undefined} data-placeholder="pedagogical">{t(k, params)}</Tag>;
}
/** Discreet seal: what is on screen comes from synthetic development data, not from the engine. */
export function SyntheticBadge({ compact }: { compact?: boolean }) {
  return <span className="ec-chip ec-chip--synthetic" title={t("synthetic.long")}><Icon name="flask" size={14} />{compact ? t("synthetic.short") : t("synthetic.badge")}</span>;
}
export function Chip({ tone, icon, children }: { tone?: "warning" | "danger" | "success" | "info"; icon?: string; children: ReactNode }) {
  return <span className={cls("ec-chip", tone && `ec-chip--${tone}`)}>{icon && <Icon name={icon} size={14} />}{children}</span>;
}

// ---- screen reader announcements
const useAnnouncer = create<{ polite: string; assertive: string }>(() => ({ polite: "", assertive: "" }));
export function announce(message: string, urgent = false) { useAnnouncer.setState(urgent ? { assertive: message } : { polite: message }); }
export function LiveRegions() {
  const { polite, assertive } = useAnnouncer();
  return (<><div className="ec-sr-only" aria-live="polite" aria-atomic="true">{polite}</div><div className="ec-sr-only" aria-live="assertive" aria-atomic="true">{assertive}</div></>);
}

export interface Column<R> { key: string; header: string; numeric?: boolean; render: (row: R) => ReactNode }
export function DataTable<R>({ caption, columns, rows, rowKey, maxHeight = 320 }: { caption: string; columns: Column<R>[]; rows: R[]; rowKey: (r: R, i: number) => string; maxHeight?: number }) {
  return (
    <div className="ec-scroll" style={{ maxHeight }} tabIndex={0} role="region" aria-label={caption}>
      <table className="ec-table">
        <caption className="ec-sr-only">{caption}</caption>
        <thead><tr>{columns.map((c) => <th key={c.key} scope="col" className={c.numeric ? "ec-num" : undefined}>{c.header}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={rowKey(r, i)}>{columns.map((c) => <td key={c.key} className={c.numeric ? "ec-num" : undefined}>{c.render(r)}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

/** Frame for every chart: title, text summary for screen readers, and an alternative table view (section 10). */
export function ChartFrame({ title, summary, table, children, actions, why }: { title: string; summary: string; table?: ReactNode; children: ReactNode; actions?: ReactNode; why?: ReactNode }) {
  const [showTable, setShowTable] = useState(false);
  const id = useId();
  return (
    <section className="ec-card" aria-labelledby={id}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 id={id}>{title}</h3>
        <div className="flex flex-wrap items-center gap-2">{actions}{table && <Button icon={showTable ? "chart" : "table"} aria-pressed={showTable} onClick={() => setShowTable(!showTable)}>{showTable ? t("chart.showChart") : t("chart.showTable")}</Button>}</div>
      </div>
      <p className="ec-muted mb-2 text-[length:var(--ec-text-sm)]" data-chart-summary>{summary}</p>
      {showTable && table ? table : <div role="img" aria-label={`${title}. ${summary}`}>{children}</div>}
      {why}
    </section>
  );
}
