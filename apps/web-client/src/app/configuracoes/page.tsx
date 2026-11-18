"use client";
import { AppShell, RoleSelector, SettingsForm, STUDENT_NAV } from "@/features/shell/Menu";
import { t } from "@/i18n";
import { useSettings } from "@/store/settingsStore";

export default function SettingsPage() {
  const dev = useSettings((s) => s.devMode);
  return (
    <AppShell title={t("settings.title")} nav={STUDENT_NAV} navLabel={t("nav.student")}>
      <section className="ec-card"><SettingsForm /></section>
      {dev && <section className="ec-card mt-3"><h2 className="mb-2">{t("role.title")}</h2><p className="ec-muted mb-2">{t("role.devOnly")}</p><RoleSelector /></section>}
    </AppShell>
  );
}
