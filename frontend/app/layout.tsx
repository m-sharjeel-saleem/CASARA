import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "CASARA — Automated PR Security Review",
  description:
    "Contextual Automated Security Analysis and Risk Assessment. Scanner-grounded multi-agent review for GitHub pull requests, with composite risk scoring and merge gating.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable} dark`}>
      <body className="min-h-screen bg-bg font-sans antialiased">
        <div className="bg-mesh pointer-events-none fixed inset-0 -z-10" />
        <div className="bg-grid pointer-events-none fixed inset-0 -z-10 opacity-40" />
        {children}
      </body>
    </html>
  );
}
