import type { Metadata, Viewport } from 'next';
import { Geist } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'ECOSFERA — Entre no seu planeta',
  description:
    'Continue moldando seu planeta vivo. Tela de acesso do ECOSFERA, um jogo educacional sobre evolução planetária e o surgimento da vida.',
};

export const viewport: Viewport = {
  themeColor: '#04060d',
  colorScheme: 'dark',
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full bg-space-void text-soft">{children}</body>
    </html>
  );
}
