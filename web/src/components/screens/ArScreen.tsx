"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useWanas } from "@/components/Providers";
import { getArModel } from "@/lib/ar-models";

/**
 * A-Frame and AR.js are vendored under `web/public/vendor/` (see NOTICE there).
 *
 * Loading them from our own origin is what lets the whole platform — AR
 * included — run with the network cable pulled, which is the state a competition
 * demo has to survive. The CDN URLs remain only as a fallback for the case where
 * the vendored files are missing from a deployment.
 */
const AFRAME_SRC = "/vendor/aframe.min.js";
const AFRAME_FALLBACK = "https://aframe.io/releases/1.4.0/aframe.min.js";
const ARJS_SRC = "/vendor/aframe-ar.js";
const ARJS_FALLBACK =
  "https://cdn.jsdelivr.net/gh/AR-js-org/AR.js@3.4.5/aframe/build/aframe-ar.js";

/** The standard Hiro fiducial marker AR.js ships a preset for. */
const LOCAL_MARKER = "/vendor/hiro.png";
const REMOTE_MARKER =
  "https://raw.githubusercontent.com/AR-js-org/AR.js/master/data/images/hiro.png";

function loadScript(src: string, fallback?: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`);
    if (existing) {
      if (existing.dataset.loaded === "true") resolve();
      else existing.addEventListener("load", () => resolve(), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    // Order matters: AR.js expects AFRAME on window, so neither may be deferred.
    script.async = false;
    script.addEventListener("load", () => {
      script.dataset.loaded = "true";
      resolve();
    });
    script.addEventListener("error", () => {
      script.remove();
      if (fallback) loadScript(fallback).then(resolve, reject);
      else reject(new Error(`failed to load ${src}`));
    });
    document.head.appendChild(script);
  });
}

export function ArScreen() {
  const { locale, t } = useWanas();
  const router = useRouter();
  const params = useSearchParams();
  const model = getArModel(params.get("site"));

  const [stage, setStage] = useState<"briefing" | "active" | "error">("briefing");
  const [markerVisible, setMarkerVisible] = useState(false);
  const [found, setFound] = useState(false);
  const [markerSrc, setMarkerSrc] = useState(LOCAL_MARKER);
  const container = useRef<HTMLDivElement>(null);

  const teardown = useCallback(() => {
    container.current?.querySelector("a-scene")?.remove();
    // AR.js leaves its video element attached to the body when the scene goes.
    document.querySelectorAll("video#arjs-video").forEach((node) => node.remove());
    setFound(false);
  }, []);

  useEffect(() => teardown, [teardown]);

  const start = async () => {
    try {
      // Ask for the camera before booting AR.js, so a refusal produces our
      // recovery screen rather than the library's silent black rectangle.
      const probe = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      probe.getTracks().forEach((track) => track.stop());

      await loadScript(AFRAME_SRC, AFRAME_FALLBACK);
      await loadScript(ARJS_SRC, ARJS_FALLBACK);
    } catch {
      setStage("error");
      return;
    }

    setStage("active");
    // The scene is raw markup: A-Frame drives custom elements imperatively and
    // does not survive React re-rendering its children.
    requestAnimationFrame(() => {
      if (!container.current) return;
      container.current.insertAdjacentHTML(
        "beforeend",
        `
        <a-scene embedded vr-mode-ui="enabled: false"
                 renderer="antialias: true; alpha: true"
                 arjs="sourceType: webcam; debugUIEnabled: false; detectionMode: mono_and_matrix;">
          <a-marker preset="hiro" id="wanas-marker" smooth="true" smoothCount="10" smoothTolerance="0.01">
            <a-entity animation="property: rotation; to: 0 360 0; loop: true; dur: 26000; easing: linear">
              ${model.markup}
            </a-entity>
          </a-marker>
          <a-entity camera></a-entity>
        </a-scene>`,
      );
      const marker = container.current.querySelector("#wanas-marker");
      marker?.addEventListener("markerFound", () => setFound(true));
      marker?.addEventListener("markerLost", () => setFound(false));
    });
  };

  const exit = () => {
    teardown();
    setStage("briefing");
    router.push(`/${locale}`);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-primary-dark">
      {stage === "active" && (
        <>
          <div ref={container} className="absolute inset-0" />
          <div className="pointer-events-none absolute inset-x-0 top-0 z-[60] flex items-center justify-between p-4">
            <span className="font-display text-[17px] font-bold text-white drop-shadow">
              WAN<span className="text-accent">AS</span>
            </span>
            <button
              type="button"
              onClick={exit}
              className="pointer-events-auto flex h-9 w-9 items-center justify-center rounded-full bg-black/45 text-lg text-white"
              aria-label={t.ar.exit}
            >
              ✕
            </button>
          </div>
          <div className="pointer-events-none absolute inset-x-0 bottom-8 z-[60] flex justify-center px-6">
            <span
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-[12.5px] font-semibold text-white backdrop-blur ${
                found ? "bg-primary/85" : "bg-black/50"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${found ? "bg-accent" : "animate-blink bg-white/70"}`}
              />
              {found ? `${model.title} — ${t.ar.found}` : t.ar.searching}
            </span>
          </div>
        </>
      )}

      {stage === "briefing" && (
        <div className="flex h-full flex-col items-center justify-center overflow-y-auto px-6 py-8 text-center text-white">
          <div className="mb-3 text-[12px] font-extrabold uppercase tracking-[0.12em] text-accent">
            {t.ar.eyebrow}
          </div>
          <h1 className="m-0 mb-2 font-display text-[clamp(28px,8vw,46px)] font-bold leading-tight">
            {t.ar.title}
          </h1>
          <p className="mb-7 max-w-[380px] text-[15px] leading-relaxed text-[#CFE3DA]">
            {t.ar.subtitle}
          </p>

          <ol className="mb-8 w-full max-w-[360px] list-none space-y-2.5 p-0 text-start">
            {[t.ar.step1, t.ar.step2, t.ar.step3].map((step, index) => (
              <li
                key={step}
                className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3"
              >
                <span className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full bg-accent text-[13px] font-extrabold text-ink">
                  {index + 1}
                </span>
                <span className="text-[13.5px] leading-snug text-[#E8F0EB]">{step}</span>
              </li>
            ))}
          </ol>

          <button
            type="button"
            onClick={start}
            className="mb-3 rounded-full bg-accent px-7 py-3.5 text-[15px] font-extrabold text-ink"
          >
            {t.ar.start}
          </button>
          <button
            type="button"
            onClick={() => setMarkerVisible(true)}
            className="text-[13px] font-bold text-[#CFE3DA] underline underline-offset-4"
          >
            {t.ar.showMarker} ↗
          </button>
          <button type="button" onClick={exit} className="mt-6 text-[12.5px] text-white/60">
            {t.common.back}
          </button>
        </div>
      )}

      {stage === "error" && (
        <div className="flex h-full flex-col items-center justify-center px-7 text-center text-white">
          <h2 className="m-0 mb-4 font-display text-[24px] font-semibold">{t.ar.cameraError}</h2>
          <ul className="m-0 mb-6 max-w-[380px] list-disc space-y-2 text-start text-[13px] leading-snug text-[#CFE3DA]">
            {t.ar.cameraHelp.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => setStage("briefing")}
            className="rounded-full bg-accent px-6 py-3 text-[14px] font-extrabold text-ink"
          >
            {t.ar.retry}
          </button>
          <button type="button" onClick={exit} className="mt-4 text-[12.5px] text-white/60">
            {t.common.back}
          </button>
        </div>
      )}

      {markerVisible && (
        <div
          className="absolute inset-0 z-[70] flex flex-col items-center justify-center gap-4 bg-white px-6 text-center"
          role="dialog"
          aria-modal="true"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={markerSrc}
            alt="WANAS AR marker"
            className="w-[260px] max-w-full border border-line"
            onError={() => markerSrc === LOCAL_MARKER && setMarkerSrc(REMOTE_MARKER)}
          />
          <p className="m-0 max-w-[360px] text-[13px] leading-snug text-muted">{t.ar.markerHint}</p>
          <button type="button" onClick={() => setMarkerVisible(false)} className="btn-primary">
            {t.ar.close}
          </button>
        </div>
      )}
    </div>
  );
}
