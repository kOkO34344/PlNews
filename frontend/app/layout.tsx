import "./globals.css";
import type { Metadata } from "next";
import { LocaleProvider } from "@/components/LocaleContext";
import { Bricolage_Grotesque, IBM_Plex_Mono, Literata } from "next/font/google";

const display = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

// Literata for the body: it is a reading face, and it carries Cyrillic — Bulgarian
// source names and quoted headlines have to set in the same type as everything else.
const body = Literata({
  subsets: ["latin", "cyrillic"],
  variable: "--font-body",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "3-3-3 · Democracy-Aware News Analyst",
  description:
    "Nine stories a day from Bulgarian politics, global politics and AI/tech/business, each read for what happened, how it was framed, and which way it moved the institutions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body>
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
