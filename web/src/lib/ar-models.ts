/**
 * Lightweight A-Frame reconstructions, one per AR-enabled site.
 *
 * These are primitives, not scanned meshes — a few hundred bytes of markup that
 * load instantly over a weak connection at a remote site. The dossier's Phase 3
 * replaces them with surveyed models; the scene contract below does not change
 * when it does, only the markup each entry returns.
 */

export type ArModel = {
  slug: string;
  title: string;
  subtitle: string;
  /** Inner markup of the rotating rig, in A-Frame primitives. */
  markup: string;
};

const CAPTION = "AI + Augmented Reality Reconstruction · WANAS";

function labels(title: string, subtitle: string): string {
  return `
    <a-text value="${title}" position="0 1.75 0" align="center" width="3.4" color="#12463A" font="dejavu"></a-text>
    <a-text value="${subtitle}" position="0 1.58 0" align="center" width="2.1" color="#C97D4B" font="dejavu"></a-text>
    <a-text value="${CAPTION}" position="0 -0.14 0" align="center" width="1.75" color="#5C6B64" font="dejavu"></a-text>
  `;
}

/** Roman colonnade: base, columns, capitals, architrave, pediment. */
function colonnade(columns: number, span: number): string {
  const step = span / (columns - 1);
  const start = -span / 2;
  let markup = `<a-box position="0 0.025 0" width="${span + 0.3}" height="0.05" depth="1.1" color="#B7A783" shadow></a-box>`;
  for (let i = 0; i < columns; i += 1) {
    const x = (start + i * step).toFixed(3);
    markup += `
      <a-cylinder position="${x} 0.55 0" radius="0.055" height="1" color="#EDE4CE"></a-cylinder>
      <a-cylinder position="${x} 1.06 0" radius="0.085" height="0.07" color="#DED2B4"></a-cylinder>`;
  }
  markup += `
    <a-box position="0 1.16 0" width="${span + 0.25}" height="0.11" depth="0.16" color="#D8CBA6"></a-box>
    <a-box position="-0.5 1.34 0" rotation="0 0 -18" width="1.15" height="0.06" depth="0.2" color="#C9BA92"></a-box>
    <a-box position="0.5 1.34 0" rotation="0 0 18" width="1.15" height="0.06" depth="0.2" color="#C9BA92"></a-box>`;
  return markup;
}

const MODELS: ArModel[] = [
  {
    slug: "tipasa",
    title: "TIPAZA",
    subtitle: "UNESCO World Heritage Site",
    markup: colonnade(4, 1.5) + labels("TIPAZA", "UNESCO World Heritage Site"),
  },
  {
    slug: "timgad",
    title: "TIMGAD",
    subtitle: "Arch of Trajan · c. AD 100",
    markup: `
      <a-box position="0 0.025 0" width="2.1" height="0.05" depth="1.0" color="#B7A783" shadow></a-box>
      <!-- Two piers carrying a central arched bay: the arch of Trajan. -->
      <a-box position="-0.62 0.55 0" width="0.34" height="1" depth="0.34" color="#EDE4CE"></a-box>
      <a-box position="0.62 0.55 0" width="0.34" height="1" depth="0.34" color="#EDE4CE"></a-box>
      <a-torus position="0 1.05 0" radius="0.45" radius-tubular="0.055" arc="180" rotation="0 0 0" color="#E6DCC2"></a-torus>
      <a-box position="0 1.28 0" width="1.75" height="0.14" depth="0.4" color="#D8CBA6"></a-box>
      <a-box position="0 1.42 0" width="1.5" height="0.12" depth="0.34" color="#C9BA92"></a-box>
      <a-cylinder position="-0.62 1.5 0.1" radius="0.05" height="0.28" color="#EDE4CE"></a-cylinder>
      <a-cylinder position="0.62 1.5 0.1" radius="0.05" height="0.28" color="#EDE4CE"></a-cylinder>
      ${labels("TIMGAD", "Arch of Trajan · c. AD 100")}
    `,
  },
  {
    slug: "djemila",
    title: "DJEMILA",
    subtitle: "Cuicul · Severan forum",
    markup:
      // Djémila steps down a ridge, so its platform is terraced.
      `<a-box position="0 0.025 0" width="2.1" height="0.05" depth="1.1" color="#B7A783" shadow></a-box>
       <a-box position="0 0.11 -0.28" width="1.7" height="0.12" depth="0.5" color="#AD9E7B"></a-box>` +
      colonnade(5, 1.6) +
      labels("DJEMILA", "Cuicul · Severan forum"),
  },
  {
    slug: "qalaa-beni-hammad",
    title: "QAL'A BENI HAMMAD",
    subtitle: "Hammadid capital · founded 1007",
    markup: `
      <a-box position="0 0.025 0" width="2.0" height="0.05" depth="1.1" color="#B7A783" shadow></a-box>
      <!-- The surviving minaret of the great mosque, square in plan. -->
      <a-box position="0 0.75 0" width="0.42" height="1.4" depth="0.42" color="#D9C9A6"></a-box>
      <a-box position="0 1.5 0" width="0.3" height="0.22" depth="0.3" color="#C9B68E"></a-box>
      <a-box position="0 1.65 0" width="0.16" height="0.12" depth="0.16" color="#B7A276"></a-box>
      <!-- Ruined courtyard walls at ankle height. -->
      <a-box position="-0.72 0.16 0" width="0.12" height="0.28" depth="1.0" color="#C4B590"></a-box>
      <a-box position="0.72 0.16 0" width="0.12" height="0.28" depth="1.0" color="#C4B590"></a-box>
      <a-box position="0 0.16 -0.48" width="1.5" height="0.28" depth="0.12" color="#C4B590"></a-box>
      ${labels("QAL'A BENI HAMMAD", "Hammadid capital · founded 1007")}
    `,
  },
];

export const DEFAULT_AR_SLUG = "tipasa";

export function getArModel(slug: string | null): ArModel {
  return MODELS.find((model) => model.slug === slug) ?? MODELS[0];
}

export const AR_SLUGS = MODELS.map((model) => model.slug);
