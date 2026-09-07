"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Icon } from "@/components/Icon";
import { useWanas } from "@/components/Providers";
import { ApiError, api, type Source, type VisionResult } from "@/lib/api";

type Turn = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  provider?: string;
  refused?: boolean;
};

type Level = "child" | "standard" | "expert";

export function GuideScreen() {
  const { locale, t } = useWanas();
  const params = useSearchParams();
  const seeded = useRef(false);

  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [level, setLevel] = useState<Level>("standard");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vision, setVision] = useState<VisionResult | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const send = async (question: string) => {
    const text = question.trim();
    if (!text || pending) return;
    setError(null);
    setDraft("");
    setTurns((prev) => [...prev, { role: "user", content: text }]);
    setPending(true);
    try {
      const answer = await api.ask({
        question: text,
        language: locale,
        level,
        conversation_id: conversationId,
      });
      setConversationId(answer.conversation_id);
      setTurns((prev) => [
        ...prev,
        {
          role: "assistant",
          content: answer.answer,
          sources: answer.sources,
          provider: answer.provider,
          refused: answer.refused,
        },
      ]);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429
          ? t.guide.quota
          : err instanceof ApiError && err.status === 0
            ? t.common.apiDown
            : t.guide.error,
      );
    } finally {
      setPending(false);
    }
  };

  // A chip tapped on the home screen arrives as ?q= and asks itself, once.
  useEffect(() => {
    const seed = params.get("q");
    if (seed && !seeded.current) {
      seeded.current = true;
      void send(seed);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns, pending]);

  const identify = async (file: File) => {
    setPending(true);
    setError(null);
    setVision(null);
    try {
      // A GPS fix turns a guess into a measurement, so ask for one — but never
      // block on it: permission may be denied, and the photo may carry EXIF.
      const fix = await new Promise<GeolocationCoordinates | null>((resolve) => {
        if (!navigator.geolocation) return resolve(null);
        const timer = setTimeout(() => resolve(null), 4000);
        navigator.geolocation.getCurrentPosition(
          (position) => {
            clearTimeout(timer);
            resolve(position.coords);
          },
          () => {
            clearTimeout(timer);
            resolve(null);
          },
          { timeout: 4000 },
        );
      });
      setVision(await api.identifyPhoto(file, locale, fix));
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? t.guide.quota : t.guide.error);
    } finally {
      setPending(false);
    }
  };

  return (
    <section className="screen flex h-full flex-col">
      <div className="eyebrow">{t.guide.eyebrow}</div>
      <h1 className="page-title">{t.guide.title}</h1>
      <p className="sub">{t.guide.subtitle}</p>

      <div className="mb-3 flex items-center gap-1.5">
        <span className="text-[11px] font-bold uppercase tracking-wide text-muted">
          {t.guide.level.label}
        </span>
        {(["child", "standard", "expert"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setLevel(option)}
            className={`lang-chip ${level === option ? "lang-chip-active" : ""}`}
          >
            {t.guide.level[option]}
          </button>
        ))}
      </div>

      <div ref={scroller} className="flex flex-1 flex-col gap-3 overflow-y-auto pb-3">
        {turns.length === 0 && !vision && (
          <div className="card">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider text-primary">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" /> WANAS
            </div>
            <p className="m-0 text-[13.5px] leading-relaxed text-ink">{t.guide.sourcesHint}</p>
          </div>
        )}

        {turns.map((turn, index) =>
          turn.role === "user" ? (
            <div key={index} className="bubble bubble-user">
              {turn.content}
            </div>
          ) : (
            <div key={index}>
              <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider text-primary">
                <span className="h-1.5 w-1.5 rounded-full bg-accent" /> WANAS
                {turn.provider === "offline" && (
                  <span className="font-bold normal-case tracking-normal text-muted">
                    · {t.common.offline}
                  </span>
                )}
              </div>
              <div className="bubble bubble-bot whitespace-pre-wrap">{turn.content}</div>
              {turn.sources && turn.sources.length > 0 && <Sources sources={turn.sources} label={t.guide.sources} />}
            </div>
          ),
        )}

        {vision && <VisionCard result={vision} />}

        {pending && (
          <div className="flex w-fit gap-1 self-start rounded-2xl rounded-bl-[4px] border border-line bg-white px-4 py-3">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 animate-blink rounded-full bg-muted"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </div>
        )}

        {error && (
          <p className="rounded-xl bg-secondary/10 px-3 py-2 text-[12.5px] text-secondary">{error}</p>
        )}
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void send(draft);
        }}
        className="sticky bottom-0 flex items-center gap-2 bg-cream pb-2 pt-2"
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={t.guide.placeholder}
          className="field flex-1"
          aria-label={t.guide.placeholder}
        />
        <input
          ref={fileInput}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void identify(file);
            event.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-line bg-white text-primary"
          aria-label={t.guide.photo}
          title={t.guide.photoHint}
        >
          <Icon name="camera" className="h-4 w-4" />
        </button>
        <button
          type="submit"
          disabled={pending || !draft.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white disabled:opacity-40"
          aria-label={t.guide.send}
        >
          <Icon name="send" className="h-4 w-4 rtl:-scale-x-100" strokeWidth={2.2} />
        </button>
      </form>
    </section>
  );
}

function Sources({ sources, label }: { sources: Source[]; label: string }) {
  return (
    <details className="mt-1.5 rounded-xl border border-line bg-white/70 px-3 py-2">
      <summary className="cursor-pointer text-[11px] font-bold uppercase tracking-wide text-secondary">
        {label} ({sources.length})
      </summary>
      <ul className="m-0 mt-2 list-none space-y-1.5 p-0">
        {sources.map((source) => (
          <li key={source.id} className="text-[11.5px] leading-snug text-muted">
            <span className="font-bold text-primary">[{source.ref}]</span> {source.title}
            <span className="block italic opacity-80">{source.source}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function VisionCard({ result }: { result: VisionResult }) {
  const { locale, t } = useWanas();
  if (!result.site) {
    return (
      <div className="card">
        <p className="m-0 text-[13px] text-ink">{t.guide.unidentified}</p>
        {result.nearby.length > 0 && (
          <ul className="m-0 mt-2 list-none space-y-1 p-0">
            {result.nearby.map((site) => (
              <li key={site.id} className="text-[12.5px] text-muted">
                · {(locale === "ar" || locale === "dz") && site.name_ar ? site.name_ar : site.name}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  const method = t.guide.method[result.method as "visual" | "geolocation"] ?? result.method;
  return (
    <div className="card">
      <div className="mb-1 flex items-center justify-between">
        <strong className="font-display text-[15px] text-primary-dark">
          {(locale === "ar" || locale === "dz") && result.site.name_ar
            ? result.site.name_ar
            : result.site.name}
        </strong>
        <span className="text-[10.5px] font-bold uppercase tracking-wide text-secondary">
          {method} · {Math.round(result.confidence * 100)}% {t.guide.confidence}
        </span>
      </div>
      <p className="m-0 whitespace-pre-wrap text-[13px] leading-relaxed text-ink">
        {result.narrative}
      </p>
      {result.sources.length > 0 && <Sources sources={result.sources} label={t.guide.sources} />}
    </div>
  );
}
