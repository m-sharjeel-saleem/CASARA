import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Sora } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });
const sora = Sora({ subsets: ["latin"], weight: ["500", "600", "700", "800"], variable: "--font-display" });

export const metadata: Metadata = {
  title: "CASARA — AI Code Security Guardrail",
  description:
    "An AI-powered security guardrail for pull requests. Scanner-grounded multi-agent review, AI-generated-code & supply-chain detection, composite risk scoring, merge gating, and one-click fixes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable} ${sora.variable} dark`}>
      <body className="min-h-screen bg-bg font-sans antialiased">
        <div className="bg-field pointer-events-none fixed inset-0 -z-10" />
        <div className="bg-grid pointer-events-none fixed inset-0 -z-10" />
        {children}
      </body>
    </html>
  );
}
