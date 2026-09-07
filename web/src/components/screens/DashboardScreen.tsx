"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { useWanas } from "@/components/Providers";
import { ApiError, api, type Dashboard } from "@/lib/api";

export function DashboardScreen() {
  const { locale, t } = useWanas();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch((err) =>
        setError(
          err instanceof ApiError && (err.status === 403 || err.status === 401)
            ? t.dashboard.restricted
            : t.common.error,
        ),
      );
  }, [t.dashboard.restricted, t.common.error]);

  return (
    <section className="screen">
      <div className="mb-3 flex items-center justify-between">
        <Link
          href={`/${locale}/profile`}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-line bg-white text-primary"
          aria-label={t.common.back}
        >
          <Icon name="chevronLeft" className="h-4 w-4 rtl:rotate-180" strokeWidth={2.2} />
        </Link>
        <span className="rounded-full bg-accent/25 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wide text-primary-dark">
          Phase 3
        </span>
      </div>

      <div className="eyebrow">{t.dashboard.eyebrow}</div>
      <h1 className="page-title">{t.dashboard.title}</h1>
      <p className="sub">{t.dashboard.subtitle}</p>

      {error && (
        <p className="rounded-xl bg-secondary/10 px-3 py-2.5 text-[12.5px] text-secondary">
          {error}
        </p>
      )}

      {data && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3">
            <Stat
              value={data.active_visitors?.toLocaleString(locale) ?? "—"}
              label={t.dashboard.activeVisitors}
            />
            <Stat
              value={
                data.average_stay_days ? `${data.average_stay_days} ${t.dashboard.days}` : "—"
              }
              label={t.dashboard.averageStay}
            />
          </div>

          <div className="section-title !mt-0">{t.dashboard.byRegion}</div>
          {data.by_region.length === 0 ? (
            <p className="text-[12.5px] text-muted">{t.dashboard.noData}</p>
          ) : (
            data.by_region.map((row) => (
              <div key={row.region} className="mb-2 flex items-center gap-3">
                <div className="w-[86px] shrink-0 text-[12px] font-semibold text-ink">
                  {row.region}
                </div>
                <div className="h-1.5 flex-1 overflow-hidden rounded bg-line">
                  <div
                    className="h-full rounded bg-primary"
                    style={{ width: `${Math.round(row.share_of_peak * 100)}%` }}
                  />
                </div>
                <div className="w-[54px] shrink-0 text-end text-[11.5px] font-bold text-muted">
                  {row.visitors}
                </div>
              </div>
            ))
          )}

          <div className="section-title">{t.dashboard.trends}</div>
          {data.trends.length === 0 ? (
            <p className="text-[12.5px] text-muted">{t.dashboard.noData}</p>
          ) : (
            data.trends.map((trend) => (
              <div
                key={trend.region}
                className={`mb-1.5 rounded-xl px-3 py-2 text-[12.5px] font-semibold ${
                  trend.direction === "up"
                    ? "bg-primary/10 text-primary"
                    : "bg-secondary/10 text-secondary"
                }`}
              >
                {trend.direction === "up" ? "▲" : "▼"} {trend.region}{" "}
                <b>
                  {trend.change_pct > 0 ? "+" : ""}
                  {trend.change_pct}%
                </b>
              </div>
            ))
          )}

          {data.suppressed.length > 0 && (
            <>
              <div className="section-title">{t.dashboard.suppressed}</div>
              <p className="text-[12px] leading-snug text-muted">{t.dashboard.suppressedHint}</p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {data.suppressed.map((cell) => (
                  <span
                    key={cell}
                    className="rounded-full border border-dashed border-line px-2.5 py-1 text-[11px] text-muted"
                  >
                    {cell}
                  </span>
                ))}
              </div>
            </>
          )}

          <div className="mt-5 flex items-start gap-2 rounded-xl bg-white px-3 py-2.5 text-[11.5px] leading-snug text-muted">
            <Icon name="lock" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
            <span>{t.dashboard.privacy}</span>
          </div>
        </>
      )}
    </section>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="card !p-3.5">
      <div className="font-display text-[22px] font-semibold text-primary-dark">{value}</div>
      <div className="mt-0.5 text-[11.5px] leading-snug text-muted">{label}</div>
    </div>
  );
}
