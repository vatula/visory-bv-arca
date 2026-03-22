import type { Metadata } from "next";
import "./globals.css";
import faviconPng from "../../assets/img/favicon.png";

export const metadata: Metadata = {
  title: "ARCRA — Agentic Observability Console",
  description: "Real-time visibility into the ARCRA autonomous reconciliation agent.",
  icons: {
    icon: faviconPng.src,
  },
};

interface RootLayoutProps {
  readonly children: React.ReactNode;
}

export default function RootLayout({
  children,
}: RootLayoutProps): React.JSX.Element {
  return (
    <html lang="en" className="bg-gray-950 text-white antialiased">
      <head>
        {/* trace_id injected server-side for distributed telemetry (AGENTS.md) */}
        <meta name="x-trace-id" content="" />
      </head>
      <body className="min-h-screen">
        <header className="border-b border-white/10 bg-gray-950 px-6 py-4">
          <div className="mx-auto flex max-w-7xl items-center gap-3">
            <span className="text-xl font-bold tracking-tight text-white">
              ARCRA
            </span>
            <span className="rounded bg-indigo-900/60 px-2 py-0.5 text-xs font-semibold text-indigo-300">
              Observability Console
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
