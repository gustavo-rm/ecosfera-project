"use client";
import Link from "next/link";
import { RoleSelector } from "@/features/shell/Menu";
import { t } from "@/i18n";
import { useSettings } from "@/store/settingsStore";
import { Icon } from "@/ui/icons";
import { Ped, SyntheticBadge } from "@/ui/kit";

/** Entry point: demonstration mode for the student, and the simulated role selector in development mode. */
export default function Home() {
  const dev = useSettings((s) => s.devMode);
  return (
    <main id="conteudo" className="mx-auto flex min-h-dvh max-w-3xl flex-col items-start justify-center gap-5 p-6" data-screen="home">
      <p className="ec-display flex items-center gap-3 text-[length:var(--ec-text-3xl)] font-bold tracking-wide"><Icon name="globe" size={44} style={{ color: "var(--ec-primary)" }} />ECOSFERA</p>
      <h1>{t("home.title")}</h1>
      <Ped as="p" k="ped.home.lead" className="max-w-prose text-[length:var(--ec-text-lg)]" />
      <div className="flex flex-wrap gap-3">
        <Link href="/jogo" className="ec-btn ec-btn--primary ec-btn--lg"><Icon name="play" />{t("home.demo")}</Link>
        <Link href="/jogo/genese" className="ec-btn ec-btn--lg"><Icon name="seed" />{t("home.create")}</Link>
        <Link href="/configuracoes" className="ec-btn ec-btn--lg"><Icon name="settings" />{t("settings.title")}</Link>
      </div>
      <p className="flex flex-wrap items-center gap-2"><SyntheticBadge /><span className="ec-muted text-[length:var(--ec-text-sm)]">{t("synthetic.long")}</span></p>
      {dev && (
        <section className="ec-card w-full" aria-labelledby="papeis">
          <h2 id="papeis" className="mb-1">{t("role.title")}</h2><p className="ec-muted mb-2 text-[length:var(--ec-text-sm)]">{t("role.devOnly")}</p><RoleSelector />
        </section>
      )}
      <p className="ec-muted text-[length:var(--ec-text-xs)]">{t("home.privacy")}</p>
    </main>
  );
}
