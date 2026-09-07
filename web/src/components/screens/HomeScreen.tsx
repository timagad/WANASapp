"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { useWanas } from "@/components/Providers";
import { SiteCard } from "@/components/SiteCard";
import { api, type Recommendation } from "@/lib/api";

type SavedItinerary = { id: string; title: string; days: number; stops: number };

export function HomeScreen() {
  const { locale, t, user } = useWanas();
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null);
  const [itinerary, setItinerary] = useState<SavedItinerary | null>(null);

  useEffect(() => {
    api
      .recommended(8)
      .then(setRecommendations)
      .catch(() => setRecommendations([]));
  }, [user]);

  useEffect(() => {
    if (!user) {
      setItinerary(null);
      return;
    }
    api
      .myItineraries()
      .then((list) => setItinerary(list[0] ?? null))
      .catch(() => setItinerary(null));
  }, [user]);

  return (
    <section className="screen">
      <div className="mb-4 flex items-center justify-between pt-1.5">
        <div className="font-display text-[19px] font-bold text-primary-dark">
          WAN<span className="text-secondary">AS</span>
        </div>
        <Link
          href={`/${locale}/profile`}
          className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-gradient-to-br from-secondary to-accent text-[13px] font-bold text-white"
          aria-label={t.nav.profile}
        >
          {(user?.name ?? "W").charAt(0).toUpperCase()}
        </Link>
      </div>

      <Link href={`/${locale}/guide`} className="ask-bar">
        <Icon name="search" className="h-[18px] w-[18px] shrink-0 text-primary" />
        <span className="text-[13.5px] text-muted">{t.home.ask}</span>
      </Link>

      <div className="my-3.5 flex gap-2 overflow-x-auto pb-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {t.home.chips.map((chip) => (
          <Link
            key={chip}
            href={`/${locale}/guide?q=${encodeURIComponent(chip)}`}
            className="chip"
          >
            {chip}
          </Link>
        ))}
      </div>

      <div className="section-title">{t.home.progress}</div>
      {itinerary ? (
        <Link
          href={`/${locale}/itinerary?id=${itinerary.id}`}
          className="flex flex-col gap-2 rounded-[18px] bg-primary p-4 text-white"
        >
          <div className="flex items-center justify-between">
            <strong className="font-display text-[16px] font-semibold">{itinerary.title}</strong>
            <Icon name="chevron" className="h-4 w-4 rtl:rotate-180" strokeWidth={2.2} />
          </div>
          <div className="text-[12px] text-[#BFE0D3]">
            {itinerary.days} {t.home.day.toLowerCase()} · {itinerary.stops} {t.home.nextStop}
          </div>
          <div className="h-1.5 overflow-hidden rounded bg-white/20">
            <div className="h-full rounded bg-accent" style={{ width: "62%" }} />
          </div>
        </Link>
      ) : (
        <Link
          href={`/${locale}/itinerary`}
          className="flex flex-col gap-1 rounded-[18px] border border-dashed border-line bg-white p-4"
        >
          <strong className="font-display text-[15px] text-primary-dark">
            {t.home.noItinerary}
          </strong>
          <span className="text-[12.5px] text-muted">{t.home.createItinerary}</span>
        </Link>
      )}

      <div className="section-title">
        {t.home.nearby}
        <Link href={`/${locale}/itinerary`}>
          <small>{t.home.seeAll}</small>
        </Link>
      </div>

      {recommendations === null ? (
        <div className="flex gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-[150px] w-[150px] shrink-0 animate-pulse rounded-2xl bg-line/60" />
          ))}
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {recommendations.map(({ site, reason }) => (
            <SiteCard key={site.id} site={site} reason={reason} />
          ))}
        </div>
      )}
    </section>
  );
}
