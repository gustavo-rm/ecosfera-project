"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { t } from "@/i18n";
import { hydrateSettings, useSettings, type Role } from "@/store/settingsStore";
import { Icon } from "@/ui/icons";
import { Button, Dialog, LiveRegions, Select, SyntheticBadge, Toggle } from "@/ui/kit";

export const STUDENT_NAV = [
  { href: "/jogo", icon: "globe", key: "nav.game" }, { href: "/jogo/genese", icon: "seed", key: "nav.genesis" }, { href: "/jogo/codex", icon: "book", key: "nav.codex" },
  { href: "/jogo/pesquisa", icon: "flask", key: "nav.research" }, { href: "/jogo/missoes", icon: "target", key: "nav.missions" }, { href: "/jogo/dados", icon: "chart", key: "nav.data" },
];
export const TEACHER_NAV = [
  { href: "/professor", icon: "grid", key: "nav.class" }, { href: "/professor/aluno", icon: "user", key: "nav.studentView" }, { href: "/professor/bncc", icon: "table", key: "nav.bncc" },
  { href: "/professor/gestao", icon: "users", key: "nav.manage" }, { href: "/professor/desafios", icon: "flag", key: "nav.challenges" }, { href: "/professor/comparar", icon: "compare", key: "nav.comparePlanets" },
  { href: "/professor/exportar", icon: "download", key: "nav.export" }, { href: "/professor/mensagens", icon: "send", key: "nav.messages" }, { href: "/professor/privacidade", icon: "shield", key: "nav.privacy" },
];
export const ROLE_HOME: Record<Role, string> = { student: "/jogo", teacher: "/professor", coordinator: "/coordenacao", guardian: "/responsavel", developer: "/lab" };
export const ROLES: Role[] = ["student", "teacher", "coordinator", "guardian", "developer"];
const ROLE_ICON: Record<Role, string> = { student: "globe", teacher: "users", coordinator: "table", guardian: "shield", developer: "flask" };

/** Applies theme, contrast, font scale and motion classes to <html>, and hydrates preferences. */
export function AppProviders({ children }: { children: ReactNode }) {
  const s = useSettings();
  useEffect(() => { hydrateSettings(); if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") void navigator.serviceWorker.register("/sw.js").catch(() => {}); }, []);
  useEffect(() => {
    const el = document.documentElement;
    el.className = [`ec-theme-${s.theme}`, s.contrast === "high" ? "ec-contrast-high" : "", s.motion === "reduced" ? "ec-motion-reduced" : s.motion === "system" ? "ec-motion-system" : ""].join(" ");
    el.style.setProperty("--ec-font-scale", String(s.fontScale));
  }, [s.theme, s.contrast, s.motion, s.fontScale]);
  return <><a href="#conteudo" className="ec-skip">{t("a11y.skip")}</a>{children}<LiveRegions /></>;
}

/** Accessibility and display preferences (RF-058, RNF-015 to RNF-019). */
export function SettingsForm() {
  const s = useSettings();
  return (
    <div className="grid gap-3 sm:grid-cols-2" data-settings>
      <Select label={t("settings.theme")} value={s.theme} onChange={(v) => s.update({ theme: v })} options={[{ value: "dark", label: t("settings.theme.dark") }, { value: "light", label: t("settings.theme.light") }]} />
      <Select label={t("settings.palette")} value={s.palette} onChange={(v) => s.update({ palette: v })} options={[{ value: "default", label: t("settings.palette.default") }, { value: "cividis", label: t("settings.palette.cividis") }, { value: "gray", label: t("settings.palette.gray") }]} />
      <Select label={t("settings.fontScale")} value={String(s.fontScale)} onChange={(v) => s.update({ fontScale: Number(v) as 1 })} options={[{ value: "1", label: "100%" }, { value: "1.15", label: "115%" }, { value: "1.3", label: "130%" }]} />
      <Select label={t("settings.motion")} value={s.motion} onChange={(v) => s.update({ motion: v })} options={[{ value: "system", label: t("settings.motion.system") }, { value: "reduced", label: t("settings.motion.reduced") }, { value: "full", label: t("settings.motion.full") }]} />
      <Toggle label={t("settings.highContrast")} icon="contrast" checked={s.contrast === "high"} onChange={(v) => s.update({ contrast: v ? "high" : "normal" })} />
      <Toggle label={t("settings.textMode")} icon="text" checked={s.textMode} onChange={(v) => s.update({ textMode: v })} />
      <Toggle label={t("settings.sound")} icon="chat" checked={s.sound} onChange={(v) => s.update({ sound: v })} />
      <p className="ec-muted text-[length:var(--ec-text-sm)] sm:col-span-2">{t("settings.soundNote")}</p>
    </div>
  );
}

export function RoleSelector() {
  const role = useSettings((s) => s.role), update = useSettings((s) => s.update);
  return (
    <div role="radiogroup" aria-label={t("role.select")} className="flex flex-wrap gap-2" data-role-selector>
      {ROLES.map((r) => <Link key={r} href={ROLE_HOME[r]} role="radio" aria-checked={role === r} className="ec-btn" onClick={() => update({ role: r })}><Icon name={ROLE_ICON[r]} />{t(`role.${r}`)}</Link>)}
    </div>
  );
}

export function MenuDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const dev = useSettings((s) => s.devMode);
  return (
    <Dialog open={open} onClose={onClose} title={t("nav.menu")}>
      <nav aria-label={t("nav.student")} className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3">{STUDENT_NAV.map((n) => <Link key={n.href} href={n.href} className="ec-btn ec-btn--lg !justify-start" onClick={onClose}><Icon name={n.icon} />{t(n.key)}</Link>)}</nav>
      <h3 className="mb-2">{t("settings.title")}</h3>
      <SettingsForm />
      {dev && <><h3 className="mb-2 mt-4">{t("role.title")}</h3><p className="ec-muted mb-2 text-[length:var(--ec-text-sm)]">{t("role.devOnly")}</p><RoleSelector /></>}
    </Dialog>
  );
}

/** Placeholder route guard. There is no real authentication in this task: the role is a local simulated session. */
export function RoleGate({ allow, children }: { allow: Role[]; children: ReactNode }) {
  const role = useSettings((s) => s.role), hydrated = useSettings((s) => s.hydrated), dev = useSettings((s) => s.devMode);
  if (!hydrated) return null;
  if (allow.includes(role) || role === "developer") return <>{children}</>;
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-3 p-8 text-center" role="alert" data-role-gate>
      <Icon name="lock" size={36} /><h1>{t("role.gateTitle")}</h1><p>{t("role.gateBody", { role: t(`role.${role}`) })}</p><p className="ec-muted text-[length:var(--ec-text-sm)]">{t("role.gatePlaceholder")}</p>
      {dev ? <RoleSelector /> : <Link className="ec-btn ec-btn--primary" href="/">{t("app.home")}</Link>}
    </div>
  );
}

/** Page shell for everything that is not the full-screen game: header, navigation by role, main landmark. */
export function AppShell({ title, nav, children, wide, navLabel }: { title: string; nav: { href: string; icon: string; key: string }[]; children: ReactNode; wide?: boolean; navLabel: string }) {
  const path = usePathname();
  const dev = useSettings((s) => s.devMode);
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 flex flex-wrap items-center gap-2 border-b border-ec-border-subtle bg-ec-surface px-3 py-2">
        <Link href="/" className="ec-display flex items-center gap-2 font-bold tracking-wide" aria-label={t("app.home")}><Icon name="globe" style={{ color: "var(--ec-primary)" }} />ECOSFERA</Link>
        <nav aria-label={navLabel} className="ec-scroll flex flex-1 gap-1">{nav.map((n) => <Link key={n.href} href={n.href} aria-current={path === n.href ? "page" : undefined} className="ec-btn whitespace-nowrap"><Icon name={n.icon} /><span className="hidden lg:inline">{t(n.key)}</span><span className="ec-sr-only lg:hidden">{t(n.key)}</span></Link>)}</nav>
        <SyntheticBadge compact />
        {dev && <Link href="/lab" className="ec-btn" aria-label={t("nav.lab")}><Icon name="flask" /></Link>}
        <Link href="/configuracoes" className="ec-btn" aria-label={t("settings.title")}><Icon name="settings" /></Link>
      </header>
      <main id="conteudo" className={`mx-auto w-full flex-1 p-3 sm:p-4 ${wide ? "max-w-[1600px]" : "max-w-6xl"}`}><h1 className="mb-3">{title}</h1>{children}</main>
    </div>
  );
}
export function StudentShell({ titleKey, children, wide }: { titleKey: string; children: ReactNode; wide?: boolean }) { return <AppShell title={t(titleKey)} nav={STUDENT_NAV} navLabel={t("nav.student")} wide={wide}>{children}</AppShell>; }
export { Button };
