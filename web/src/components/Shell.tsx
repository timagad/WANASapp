"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useWanas } from "@/components/Providers";
import { Icon } from "@/components/Icon";

const TABS = [
  { key: "home", href: "", icon: "home" },
  { key: "guide", href: "/guide", icon: "chat" },
  { key: "itinerary", href: "/itinerary", icon: "route" },
  { key: "market", href: "/market", icon: "bag" },
  { key: "profile", href: "/profile", icon: "user" },
] as const;

/** The device frame, status strip and bottom navigation shared by every screen. */
export function Shell({ children }: { children: React.ReactNode }) {
  const { locale, t, health, apiReachable } = useWanas();
  const pathname = usePathname();
  const base = `/${locale}`;

  const isActive = (href: string) => {
    const full = `${base}${href}`;
    return href === "" ? pathname === base || pathname === `${base}/` : pathname.startsWith(full);
  };

  // The AR view takes the whole viewport: a camera feed inside a fake phone
  // bezel, with a tab bar over it, would be absurd.
  if (pathname === `${base}/ar`) return <>{children}</>;

  return (
    <div className="stage">
      <div className="phone">
        <div className="hidden md:block absolute left-1/2 top-[14px] z-50 h-[26px] w-[120px] -translate-x-1/2 rounded-b-2xl bg-[#050d0a]" />
        <div className="screen-frame">
          <div className="flex shrink-0 items-center justify-between px-6 pb-1 pt-3.5 text-[13px] font-bold text-ink">
            <Clock />
            <span className="font-display tracking-wide">WANAS</span>
            <StatusPill offline={health?.llm === "offline-grounded"} unreachable={!apiReachable} />
          </div>

          {!apiReachable && (
            <p className="mx-5 mb-2 rounded-xl bg-secondary/10 px-3 py-2 text-[11.5px] leading-snug text-secondary">
              {t.common.apiDown}
            </p>
          )}

          <div className="content">{children}</div>

          <nav className="flex shrink-0 items-stretch border-t border-line bg-white/95 px-1 pb-1 pt-0.5 backdrop-blur">
            {TABS.map((tab) => (
              <Link
                key={tab.key}
                href={`${base}${tab.href}`}
                className={`nav-btn ${isActive(tab.href) ? "nav-btn-active" : ""}`}
                aria-current={isActive(tab.href) ? "page" : undefined}
              >
                <Icon name={tab.icon} className="h-[18px] w-[18px]" />
                {t.nav[tab.key]}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </div>
  );
}

/**
 * The status-bar clock, mounted client-side only.
 *
 * These pages are prerendered at build time, so rendering the current time
 * during SSR bakes the build clock into the HTML and every visitor hydrates
 * against a different value. Reserving the space and filling it after mount
 * keeps the layout from shifting without lying about the time.
 */
function Clock() {
  const [now, setNow] = useState<string | null>(null);

  useEffect(() => {
    const tick = () =>
      setNow(new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }));
    tick();
    const timer = setInterval(tick, 30_000);
    return () => clearInterval(timer);
  }, []);

  return (
    <span className="min-w-[38px]" suppressHydrationWarning>
      {now ?? ""}
    </span>
  );
}

function StatusPill({ offline, unreachable }: { offline?: boolean; unreachable: boolean }) {
  if (unreachable) return <span className="text-[10px] font-bold text-secondary">⚠︎</span>;
  return (
    <span
      className="text-[10px] font-extrabold uppercase tracking-wider text-muted"
      title={offline ? "Offline grounded provider" : "Claude"}
    >
      {offline ? "◍" : "◉"}
    </span>
  );
}
