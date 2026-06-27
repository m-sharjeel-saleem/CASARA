"use client";

import {
  BookOpen, GitPullRequest, LayoutDashboard, Radar, Settings, FolderGit2, ShieldCheck, TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/posture", label: "Posture", icon: ShieldCheck },
  { href: "/dashboard/reviews", label: "Reviews", icon: GitPullRequest },
  { href: "/dashboard/analytics", label: "Analytics", icon: TrendingUp },
  { href: "/dashboard/repositories", label: "Repositories", icon: FolderGit2 },
  { href: "/dashboard/settings", label: "Settings & Rules", icon: Settings },
  { href: "/dashboard/commands", label: "Commands", icon: BookOpen },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 border-r border-border lg:flex lg:flex-col">
      <Link href="/" className="flex h-16 items-center gap-2.5 border-b border-border px-5">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.svg" alt="" className="h-7 w-7" />
        <div className="leading-tight">
          <div className="font-display text-[15px] font-bold tracking-tight text-white">CASARA</div>
          <div className="eyebrow !text-[9px] !tracking-[0.18em]">Security Console</div>
        </div>
      </Link>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {NAV.map((item) => {
          const active = item.exact ? path === item.href : path.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active ? "bg-accent/12 text-accent-soft" : "text-slate-400 hover:bg-white/5 hover:text-slate-200",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2 rounded-lg bg-white/[0.02] px-3 py-2 text-[11px] text-slate-500">
          <Radar className="h-3.5 w-3.5 text-accent-soft" />
          <span>AI-code security guardrail</span>
        </div>
      </div>
    </aside>
  );
}

/** Mobile nav — horizontal scroll tabs shown only on small screens. */
export function MobileNav() {
  const path = usePathname();
  return (
    <nav className="flex gap-1 overflow-x-auto border-b border-border px-3 py-2 lg:hidden">
      {NAV.map((item) => {
        const active = item.exact ? path === item.href : path.startsWith(item.href);
        return (
          <Link key={item.href} href={item.href}
            className={cn("flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs",
              active ? "bg-accent/12 text-accent-soft" : "text-slate-400")}>
            <item.icon className="h-3.5 w-3.5" /> {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
