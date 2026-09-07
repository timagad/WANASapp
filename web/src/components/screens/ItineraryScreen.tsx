"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { useWanas } from "@/components/Providers";
import { siteName } from "@/components/SiteCard";
import { ApiError, api, type Itinerary } from "@/lib/api";

export function ItineraryScreen() {
  const { locale, t, user } = useWanas();
  const params = useSearchParams();
  const savedId = params.get("id");

  const [query, setQuery] = useState("");
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [activeDay, setActiveDay] = useState(1);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!savedId) return;
    api
      .itinerary(savedId)
      .then((value) => {
        setItinerary(value);
        setActiveDay(value.plan[0]?.index ?? 1);
      })
      .catch(() => setError(t.common.error));
  }, [savedId, t.common.error]);

  const generate = async () => {
    if (!query.trim() || pending) return;
    setPending(true);
    setError(null);
    try {
      const result = await api.generateItinerary({
        query,
        language: locale,
        // Saving needs an account; without one the plan is still generated,
        // just not persisted.
        save: Boolean(user),
      });
      setItinerary(result);
      setActiveDay(result.plan[0]?.index ?? 1);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 0 ? t.common.apiDown : t.common.error);
    } finally {
      setPending(false);
    }
  };

  const day = itinerary?.plan.find((d) => d.index === activeDay) ?? itinerary?.plan[0];

  return (
    <section className="screen">
      <div className="eyebrow">{t.itinerary.eyebrow}</div>
      <h1 className="page-title">{itinerary?.title ?? t.itinerary.title}</h1>
      <p className="sub">{t.itinerary.subtitle}</p>

      <div className="mb-4 flex flex-col gap-2">
        <label className="text-[11px] font-bold uppercase tracking-wide text-muted" htmlFor="trip">
          {t.itinerary.prompt}
        </label>
        <textarea
          id="trip"
          rows={2}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t.itinerary.promptPlaceholder}
          className="field resize-none"
        />
        <button type="button" onClick={generate} disabled={pending} className="btn-primary">
          <Icon name="sparkle" className="h-4 w-4" />
          {pending ? t.common.loading : t.itinerary.generate}
        </button>
        {!user && <p className="m-0 text-[11.5px] text-muted">{t.itinerary.signInToSave}</p>}
        {error && <p className="m-0 text-[12px] text-secondary">{error}</p>}
      </div>

      {!itinerary && <p className="text-[13px] text-muted">{t.itinerary.empty}</p>}

      {itinerary && (
        <>
          <div className="mb-3 flex flex-wrap gap-1.5 text-[11px] text-muted">
            <Badge>{itinerary.days} {t.itinerary.day.toLowerCase()}</Badge>
            <Badge>{itinerary.party_size} {t.itinerary.party}</Badge>
            <Badge>{t.itinerary.budget[itinerary.budget_band as "low" | "mid" | "high"]}</Badge>
            {itinerary.mobility === "limited" && <Badge>{t.itinerary.mobility.limited}</Badge>}
          </div>

          <div className="mb-4 flex gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {itinerary.plan.map((d) => (
              <button
                key={d.index}
                type="button"
                onClick={() => setActiveDay(d.index)}
                className={`chip ${d.index === activeDay ? "chip-active" : ""}`}
              >
                {t.itinerary.day} {d.index}
              </button>
            ))}
          </div>

          {day && (
            <>
              {day.travel_km > 0 && (
                <p className="mb-3 text-[11.5px] text-muted">
                  {day.travel_km} {t.itinerary.travel}
                </p>
              )}
              <ol className="m-0 list-none space-y-0 p-0">
                {day.stops.map((stop, index) => (
                  <li key={`${stop.label}-${index}`} className="flex gap-3">
                    <div className="w-[54px] shrink-0 pt-0.5 text-[11.5px] font-bold text-primary">
                      {stop.arrive_at}
                    </div>
                    <div className="flex w-3 flex-col items-center">
                      <span className="stop-node" />
                      {index < day.stops.length - 1 && <span className="stop-line" />}
                    </div>
                    <div className="flex-1 pb-5">
                      <div className="text-[13.5px] font-bold text-ink">{stop.label}</div>
                      <div className="text-[11.5px] text-muted">
                        {stop.dwell_minutes} {t.common.minutes}
                      </div>
                      {stop.tip && (
                        <p className="mt-1 text-[12px] leading-snug text-muted">{stop.tip}</p>
                      )}
                      {stop.site?.has_ar && (
                        <Link
                          href={`/${locale}/ar?site=${stop.site.slug}`}
                          className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-[11px] font-bold text-white"
                        >
                          <Icon name="camera" className="h-3 w-3" strokeWidth={2.5} />
                          {t.itinerary.viewInAR}
                        </Link>
                      )}
                      {stop.site && (
                        <Link
                          href={`/${locale}/sites/${stop.site.slug}`}
                          className="ms-2 mt-2 inline-flex items-center gap-1 text-[11px] font-bold text-secondary"
                        >
                          {siteName(stop.site, locale)}
                          <Icon name="chevron" className="h-3 w-3 rtl:rotate-180" />
                        </Link>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </>
          )}

          {itinerary.id && (
            <p className="mt-2 text-[11.5px] font-bold text-primary">{t.itinerary.saved}</p>
          )}
        </>
      )}
    </section>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-line bg-white px-2.5 py-1 font-semibold">
      {children}
    </span>
  );
}
