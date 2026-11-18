import type { Metadata, Viewport } from "next";
import { AppProviders } from "@/features/shell/Menu";
import "./globals.css";

export const metadata: Metadata = {
  title: "ECOSFERA",
  description: "Crie e evolua um planeta e aprenda ciências por causa e efeito.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icons/icon.svg" },
};
export const viewport: Viewport = { themeColor: "#070b16", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className="ec-theme-dark" suppressHydrationWarning>
      <body><AppProviders>{children}</AppProviders></body>
    </html>
  );
}
