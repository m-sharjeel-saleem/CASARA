"use client";

import { Github } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

/** "Install on GitHub" CTA. Resolves the real App install URL from the backend;
 *  while loading or if the App isn't configured yet, it stays a usable link. */
export function InstallButton({ size = "lg" }: { size?: "lg" | "sm" }) {
  const [url, setUrl] = useState<string>("https://github.com/apps");

  useEffect(() => {
    api
      .installUrl()
      .then((r) => r.url && setUrl(r.url))
      .catch(() => {});
  }, []);

  const cls =
    size === "lg"
      ? "px-6 py-3 text-[15px]"
      : "px-4 py-2 text-sm";

  return (
    <a
      href={url}
      className={`inline-flex items-center gap-2 rounded-xl bg-accent font-semibold text-white shadow-glow transition hover:bg-accent-deep ${cls}`}
    >
      <Github className="h-4 w-4" />
      Install on GitHub
    </a>
  );
}
