"use client";

import { useId } from "react";

/**
 * Craft illustrations, drawn from the technique rather than the object.
 *
 * Each one uses the motif vocabulary named in that product's own listing —
 * Kabyle chevrons and diamonds on the pottery, M'Zab banding on the rug, the
 * khomessa's engraved palm on the silver — so the picture agrees with the story
 * printed beside it instead of being generic shopping art.
 */

const VIEW_BOX = "0 0 300 180";

const C = {
  clay: "#E8D7B4",
  clayDeep: "#C97D4B",
  ochre: "#A85A30",
  wool: "#E3D3B3",
  woolDeep: "#A85A30",
  silver: "#CBD4D8",
  silverDeep: "#6D7F88",
  ebony: "#2B2622",
  hide: "#A9764C",
  hideDeep: "#6B4426",
  velvet: "#5C2A3A",
  gold: "#E8B33D",
  ink: "#1F2A24",
  linen: "#F7F3EC",
} as const;

type Scene = (uid: string) => React.ReactNode;

function Ground({ id, from, to }: { id: string; from: string; to: string }) {
  return (
    <>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={from} />
          <stop offset="100%" stopColor={to} />
        </linearGradient>
      </defs>
      <rect width="300" height="180" fill={`url(#${id})`} />
    </>
  );
}

/** Chevron band, the recurring Kabyle and M'Zab motif. */
function Chevrons({ y, from, to, count, color, width = 2.4 }: {
  y: number; from: number; to: number; count: number; color: string; width?: number;
}) {
  const step = (to - from) / count;
  return (
    <g stroke={color} strokeWidth={width} fill="none" strokeLinecap="round">
      {Array.from({ length: count }).map((_, i) => (
        <path key={i} d={`M${from + i * step} ${y + 6} L${from + i * step + step / 2} ${y} L${from + (i + 1) * step} ${y + 6}`} />
      ))}
    </g>
  );
}

/** Hand-built vessel, light slip, painted geometric bands. */
const pottery: Scene = (uid) => (
  <>
    <Ground id={`${uid}g`} from="#F6EBD6" to="#E4CDA6" />
    <ellipse cx="150" cy="156" rx="62" ry="8" fill={C.ochre} opacity=".18" />
    <path
      d="M150 34 c-16 0 -22 8 -22 14 0 5 4 8 4 12 -22 10 -36 30 -36 54 0 26 24 42 54 42 s54 -16 54 -42 c0 -24 -14 -44 -36 -54 0 -4 4 -7 4 -12 0 -6 -6 -14 -22 -14 Z"
      fill={C.clay}
      stroke={C.ochre}
      strokeWidth="2"
    />
    <path d="M128 60 q22 10 44 0" fill="none" stroke={C.ochre} strokeWidth="2.2" />
    <Chevrons y={82} from={104} to={196} count={7} color={C.clayDeep} />
    {[118, 150, 182].map((x) => (
      <path key={x} d={`M${x} 104 l12 12 l-12 12 l-12 -12 Z`} fill={C.ochre} opacity=".8" />
    ))}
    <Chevrons y={134} from={106} to={194} count={6} color={C.clayDeep} />
  </>
);

/** Woven field: alternating bands and diamond lozenges, warp fringe. */
const rug: Scene = (uid) => (
  <>
    <Ground id={`${uid}g`} from="#F0E2C8" to="#D9BE93" />
    <rect x="44" y="24" width="212" height="132" fill={C.wool} stroke={C.ochre} strokeWidth="2.5" />
    {[38, 74, 110, 146].map((y, i) => (
      <rect key={y} x="48" y={y} width="204" height={i % 2 ? 10 : 6} fill={C.woolDeep} opacity={i % 2 ? 0.5 : 0.75} />
    ))}
    {[0, 1, 2, 3, 4].map((i) => (
      <path
        key={i}
        d={`M${74 + i * 38} 92 l16 16 l-16 16 l-16 -16 Z`}
        fill={C.ochre}
        opacity=".75"
      />
    ))}
    {[0, 1, 2, 3, 4].map((i) => (
      <path
        key={`o${i}`}
        d={`M${74 + i * 38} 92 l16 16 l-16 16 l-16 -16 Z`}
        fill="none"
        stroke={C.wool}
        strokeWidth="2"
      />
    ))}
    <Chevrons y={54} from={52} to={248} count={14} color={C.ochre} width={1.8} />
    {/* Warp threads left loose at both ends, as they come off the loom. */}
    {Array.from({ length: 22 }).map((_, i) => (
      <line key={i} x1={48 + i * 9.6} y1="156" x2={48 + i * 9.6} y2="168" stroke={C.woolDeep} strokeWidth="1.6" opacity=".6" />
    ))}
  </>
);

/** Khomessa: engraved silver, ebony inlay, on a tanned cord. */
const jewellery: Scene = (uid) => (
  <>
    <Ground id={`${uid}g`} from="#E7EDEF" to="#C2CED4" />
    <path d="M60 34 q90 42 180 0" fill="none" stroke={C.hideDeep} strokeWidth="3" opacity=".8" />
    <circle cx="150" cy="60" r="7" fill={C.silverDeep} />
    <path
      d="M150 70 l46 34 l-46 62 l-46 -62 Z"
      fill={C.silver}
      stroke={C.silverDeep}
      strokeWidth="2.5"
    />
    <path d="M150 84 l30 22 l-30 42 l-30 -42 Z" fill="none" stroke={C.silverDeep} strokeWidth="1.8" />
    <path d="M150 96 v52 M128 112 h44" stroke={C.silverDeep} strokeWidth="1.6" />
    <circle cx="150" cy="112" r="7" fill={C.ebony} />
    {[[122, 104], [178, 104], [150, 150]].map(([cx, cy]) => (
      <circle key={`${cx}`} cx={cx} cy={cy} r="3.4" fill={C.clayDeep} />
    ))}
    <path d="M104 104 l46 -34 l46 34" fill="none" stroke={C.silverDeep} strokeWidth="1.4" opacity=".7" />
  </>
);

/** Saddle-stitched satchel: flap, buckle, waxed thread. */
const leather: Scene = (uid) => (
  <>
    <Ground id={`${uid}g`} from="#EFE1D0" to="#CDB194" />
    <path d="M92 78 q58 -34 116 0" fill="none" stroke={C.hideDeep} strokeWidth="4" />
    <rect x="76" y="76" width="148" height="82" rx="8" fill={C.hide} stroke={C.hideDeep} strokeWidth="2.5" />
    <path d="M76 76 h148 v34 a10 10 0 0 1 -10 10 H86 a10 10 0 0 1 -10 -10 Z" fill={C.hideDeep} opacity=".9" />
    <rect x="138" y="106" width="24" height="18" rx="3" fill={C.gold} opacity=".85" />
    <rect x="144" y="112" width="12" height="6" rx="2" fill={C.hideDeep} />
    {/* Saddle stitch, the detail the listing actually claims. */}
    {[86, 214].map((x) => (
      <line key={x} x1={x} y1="128" x2={x} y2="150" stroke={C.linen} strokeWidth="2" strokeDasharray="4 5" opacity=".8" />
    ))}
    <line x1="86" y1="152" x2="214" y2="152" stroke={C.linen} strokeWidth="2" strokeDasharray="4 5" opacity=".8" />
  </>
);

/** Fetla and medjboud: gold thread couched on velvet. */
const embroidery: Scene = (uid) => (
  <>
    <Ground id={`${uid}g`} from="#7A3B4E" to="#4A2130" />
    <rect x="34" y="30" width="232" height="120" rx="4" fill={C.velvet} stroke={C.gold} strokeWidth="2" opacity=".95" />
    <path
      d="M150 52 q34 0 34 30 t-34 30 t-34 -30 t34 -30"
      fill="none"
      stroke={C.gold}
      strokeWidth="3"
    />
    <path d="M150 112 q0 22 -28 26 M150 112 q0 22 28 26" fill="none" stroke={C.gold} strokeWidth="2.4" />
    <path d="M72 66 q22 26 0 52 M228 66 q-22 26 0 52" fill="none" stroke={C.gold} strokeWidth="2.4" opacity=".85" />
    {[[150, 82], [104, 92], [196, 92]].map(([cx, cy]) => (
      <circle key={cx} cx={cx} cy={cy} r="5" fill={C.gold} />
    ))}
    {[60, 240].map((x) => (
      <circle key={x} cx={x} cy="90" r="3.4" fill={C.gold} opacity=".8" />
    ))}
  </>
);

const CRAFT_ART: Record<string, Scene> = { pottery, rug, jewellery, leather, embroidery };

export function CraftArt({ category, className = "" }: { category?: string; className?: string }) {
  const uid = `c${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const scene = CRAFT_ART[category ?? ""] ?? pottery;

  return (
    <svg
      viewBox={VIEW_BOX}
      preserveAspectRatio="xMidYMid slice"
      className={`block ${className}`}
      role="presentation"
      aria-hidden="true"
    >
      {scene(uid)}
    </svg>
  );
}
