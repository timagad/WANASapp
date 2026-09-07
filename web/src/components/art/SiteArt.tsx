"use client";

import { useId } from "react";

/**
 * Per-site illustrations, drawn from each monument's actual architecture.
 *
 * These replace the flat category gradients. They are inline SVG — a few
 * hundred bytes each, no network, no licensing, and they take the app's own
 * palette so a screen full of them reads as one system rather than a photo
 * collage. They are decorative, not documentary: enough of Timgad's arch or the
 * M'Zab's stacked ksar to be recognisable, standing in until the Phase 2
 * photography commission lands.
 */

const VIEW_BOX = "0 0 300 180";

const P = {
  seaTop: "#3a8c74",
  seaDeep: "#12463A",
  stone: "#EDE4CE",
  stoneMid: "#D8CBA6",
  stoneDark: "#B7A783",
  earth: "#C99A63",
  earthDark: "#A85A30",
  green: "#3a7d68",
  greenDark: "#1B5A48",
  night: "#0B2E25",
  gold: "#E8B33D",
  terracotta: "#C97D4B",
  white: "#F7F3EC",
  shadow: "rgba(11,46,37,.18)",
} as const;

type Scene = (uid: string) => React.ReactNode;

function Sky({ id, from, to }: { id: string; from: string; to: string }) {
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

function Column({ x, top, bottom, w = 10 }: { x: number; top: number; bottom: number; w?: number }) {
  return (
    <>
      <rect x={x} y={top} width={w} height={bottom - top} fill={P.stone} rx="1" />
      <rect x={x - 2.5} y={top - 5} width={w + 5} height="5" fill={P.stoneMid} rx="1" />
      <rect x={x - 2} y={bottom - 3} width={w + 4} height="3" fill={P.stoneDark} rx="1" />
    </>
  );
}

function Palm({ x, y, h, scale = 1 }: { x: number; y: number; h: number; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect x={-1.5 * scale} y={-h} width={3 * scale} height={h} fill={P.earthDark} rx="1" />
      {[-38, -14, 14, 38, -70, 70].map((angle) => (
        <ellipse
          key={angle}
          cx={0}
          cy={-h}
          rx={16 * scale}
          ry={4 * scale}
          fill={P.greenDark}
          transform={`rotate(${angle} 0 ${-h}) translate(${14 * scale} 0)`}
        />
      ))}
    </g>
  );
}

// --------------------------------------------------------------------------- //
// Scenes
// --------------------------------------------------------------------------- //

/** Roman colonnade above the Mediterranean, late afternoon. */
const tipasa: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#F6E2BC" to="#EFC98F" />
    <circle cx="238" cy="74" r="19" fill={P.gold} opacity=".75" />
    <rect y="104" width="300" height="22" fill={P.seaTop} />
    <rect y="118" width="300" height="10" fill={P.seaDeep} opacity=".55" />
    <rect y="126" width="300" height="54" fill={P.stoneMid} />
    <rect x="34" y="126" width="232" height="8" fill={P.stoneDark} rx="2" />
    <rect x="42" y="52" width="216" height="9" fill={P.stoneMid} rx="2" />
    <rect x="46" y="45" width="208" height="7" fill={P.stoneDark} rx="2" opacity=".8" />
    {[52, 92, 132, 172, 212].map((x) => (
      <Column key={x} x={x} top={61} bottom={126} />
    ))}
    {/* A broken shaft: this is a ruin, not a reconstruction. */}
    <rect x="252" y="96" width="10" height="30" fill={P.stone} rx="1" />
    <rect x="250" y="123" width="14" height="3" fill={P.stoneDark} rx="1" />
  </>
);

/** The arch of Trajan, three bays, on the Aurès plain. */
const timgad: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#F7E7C6" to="#E9C892" />
    <path d="M0 116 L58 92 L104 116 Z" fill={P.greenDark} opacity=".35" />
    <path d="M196 116 L252 86 L300 116 Z" fill={P.greenDark} opacity=".3" />
    <rect y="116" width="300" height="64" fill={P.earth} opacity=".5" />
    <rect y="116" width="300" height="5" fill={P.stoneDark} />
    <rect x="86" y="40" width="128" height="12" fill={P.stoneMid} rx="2" />
    <rect x="94" y="52" width="112" height="8" fill={P.stoneDark} rx="1" opacity=".75" />
    <rect x="96" y="60" width="26" height="58" fill={P.stone} />
    <rect x="178" y="60" width="26" height="58" fill={P.stone} />
    <path d="M122 118 V84 a28 28 0 0 1 56 0 v34 h-14 V84 a14 14 0 0 0 -28 0 v34 Z" fill={P.stone} />
    <rect x="100" y="30" width="8" height="12" fill={P.stoneMid} rx="1" />
    <rect x="192" y="30" width="8" height="12" fill={P.stoneMid} rx="1" />
    {/* The grid plan Timgad is known for, read as paving. */}
    {[132, 152, 172].map((y) => (
      <rect key={y} y={y} x="0" width="300" height="1.5" fill={P.stoneDark} opacity=".35" />
    ))}
  </>
);

/** Cuicul: a Roman town folded onto a mountain ridge. */
const djemila: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#EAF2E6" to="#C4D8C0" />
    <path d="M0 118 L76 58 L152 118 Z" fill={P.green} opacity=".55" />
    <path d="M132 118 L226 48 L300 118 Z" fill={P.greenDark} opacity=".5" />
    {/* The town is terraced because the ridge gave it no choice. */}
    <rect y="150" width="300" height="30" fill="#9E9068" />
    <rect y="134" width="300" height="17" fill={P.stoneDark} />
    <rect y="116" width="300" height="19" fill={P.stoneMid} />
    <rect y="116" width="300" height="3" fill={P.stone} opacity=".7" />
    <rect x="28" y="54" width="130" height="10" fill={P.stoneMid} rx="2" />
    <rect x="34" y="64" width="118" height="6" fill={P.stoneDark} rx="1" opacity=".7" />
    {[40, 72, 104, 136].map((x) => (
      <Column key={x} x={x} top={70} bottom={116} w={10} />
    ))}
    {/* The arch of Caracalla, on the lower terrace. */}
    <rect x="188" y="62" width="84" height="10" fill={P.stoneMid} rx="2" />
    <rect x="194" y="72" width="72" height="6" fill={P.stoneDark} rx="1" opacity=".7" />
    <rect x="196" y="78" width="18" height="38" fill={P.stone} />
    <rect x="246" y="78" width="18" height="38" fill={P.stone} />
    <path d="M214 116 V96 a16 16 0 0 1 32 0 v20 h-10 V96 a6 6 0 0 0 -12 0 v20 Z" fill={P.stone} />
  </>
);

/** Stacked houses stepping down to the bay, and a minaret. */
const casbahAlger: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#EAF2F4" to="#CFE0E2" />
    <rect y="140" width="300" height="40" fill={P.seaTop} />
    <rect y="158" width="300" height="22" fill={P.seaDeep} opacity=".5" />
    {[
      { x: 6, y: 96, w: 46, h: 46 },
      { x: 40, y: 74, w: 42, h: 68 },
      { x: 76, y: 58, w: 48, h: 84 },
      { x: 118, y: 82, w: 40, h: 60 },
      { x: 152, y: 62, w: 46, h: 80 },
      { x: 192, y: 90, w: 44, h: 52 },
      { x: 230, y: 70, w: 46, h: 72 },
      { x: 264, y: 100, w: 36, h: 42 },
    ].map((b, i) => (
      <g key={b.x}>
        <rect x={b.x} y={b.y} width={b.w} height={b.h} fill={i % 2 ? P.white : "#F0E7D8"} />
        <rect x={b.x} y={b.y} width={b.w} height="4" fill={P.stoneDark} opacity=".55" />
        <rect x={b.x + 8} y={b.y + 16} width="8" height="11" fill={P.night} opacity=".28" rx="1" />
        <rect x={b.x + b.w - 18} y={b.y + 16} width="8" height="11" fill={P.night} opacity=".28" rx="1" />
      </g>
    ))}
    {/* Minaret of the lower town. */}
    <rect x="128" y="24" width="17" height="60" fill={P.white} />
    <rect x="126" y="20" width="21" height="6" fill={P.stoneMid} rx="1" />
    <path d="M136.5 6 L146 20 H127 Z" fill={P.green} />
    <rect x="131" y="34" width="11" height="14" fill={P.green} opacity=".3" rx="5" />
  </>
);

/** A ksar in concentric rings, its watch-minaret at the summit. */
const valleeMzab: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#F8E5C2" to="#EDCE9A" />
    <circle cx="46" cy="46" r="16" fill={P.gold} opacity=".7" />
    <rect y="140" width="300" height="40" fill={P.earth} opacity=".55" />
    <path d="M60 142 L150 34 L240 142 Z" fill="#F0E2C6" />
    {[
      { y: 118, w: 120 },
      { y: 96, w: 92 },
      { y: 74, w: 64 },
    ].map((ring) => (
      <g key={ring.y}>
        <rect x={150 - ring.w / 2} y={ring.y} width={ring.w} height="18" fill={P.white} />
        <rect x={150 - ring.w / 2} y={ring.y} width={ring.w} height="3" fill={P.stoneDark} opacity=".5" />
        {Array.from({ length: Math.floor(ring.w / 22) }).map((_, i) => (
          <rect
            key={i}
            x={150 - ring.w / 2 + 8 + i * 22}
            y={ring.y + 7}
            width="6"
            height="8"
            fill={P.terracotta}
            opacity=".45"
            rx="1"
          />
        ))}
      </g>
    ))}
    {/* Tapering square minaret with the M'Zab's four corner horns. */}
    <path d="M143 74 L157 74 L154 30 L146 30 Z" fill={P.white} />
    <path d="M146 30 L150 16 L154 30 Z" fill={P.white} />
    <path d="M143 36 L140 26 M157 36 L160 26" stroke={P.white} strokeWidth="3" strokeLinecap="round" />
    <Palm x={40} y={158} h={30} scale={0.8} />
    <Palm x={262} y={162} h={26} scale={0.7} />
  </>
);

/** Sandstone forest, with a natural arch and rock art. */
const tassiliNajjer: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#F4D9A6" to="#E2A96E" />
    <circle cx="60" cy="52" r="15" fill={P.gold} opacity=".8" />
    <rect y="142" width="300" height="38" fill={P.earth} />
    <path d="M0 142 V80 h30 v-18 h26 v26 h18 V142 Z" fill={P.earthDark} opacity=".75" />
    <path
      d="M96 142 V70 h22 v14 a34 34 0 0 1 44 0 V70 h22 v72 h-22 V96 a20 20 0 0 0 -44 0 v46 Z"
      fill="#B8703F"
    />
    <path d="M212 142 V56 h20 v22 h16 v-14 h18 v78 Z" fill={P.earthDark} opacity=".85" />
    {/* Rock-art figures, the reason the plateau is inscribed. */}
    <g fill={P.night} opacity=".55">
      <circle cx="128" cy="118" r="3" />
      <path d="M128 121 v9 M124 124 h8 M128 130 l-4 7 M128 130 l4 7" stroke={P.night} strokeWidth="1.8" fill="none" />
      <circle cx="146" cy="120" r="2.6" />
      <path d="M146 123 v8 M142 126 h8 M146 131 l-3 6 M146 131 l3 6" stroke={P.night} strokeWidth="1.6" fill="none" />
    </g>
  </>
);

/** The surviving Hammadid minaret over a ruined enclosure. */
const qalaaBeniHammad: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#EFE6D2" to="#D9CBA6" />
    <path d="M0 108 L64 76 L128 108 Z" fill={P.greenDark} opacity=".3" />
    <path d="M170 108 L242 72 L300 108 Z" fill={P.greenDark} opacity=".25" />
    <rect y="140" width="300" height="40" fill="#9E9068" />
    <rect y="132" width="300" height="10" fill={P.stoneDark} />
    {/* The one thing still standing: the minaret of the great mosque. */}
    <rect x="132" y="26" width="38" height="106" fill="#E4D6B4" />
    <rect x="132" y="26" width="8" height="106" fill={P.stone} />
    <rect x="128" y="19" width="46" height="8" fill={P.stoneMid} rx="1" />
    <rect x="142" y="8" width="18" height="12" fill="#E4D6B4" />
    <rect x="140" y="4" width="22" height="5" fill={P.stoneMid} rx="1" />
    {[40, 66, 92].map((y) => (
      <g key={y}>
        <path d={`M144 ${y + 17} v-9 a5 5 0 0 1 10 0 v9 Z`} fill="#8C7A55" />
        <path d={`M158 ${y + 17} v-9 a5 5 0 0 1 10 0 v9 Z`} fill="#8C7A55" />
      </g>
    ))}
    {/* Wall stumps: the city was abandoned in 1090 and never rebuilt. */}
    <rect x="30" y="106" width="68" height="26" fill="#E4D6B4" />
    <rect x="30" y="106" width="68" height="4" fill="#8C7A55" />
    <rect x="52" y="116" width="14" height="16" fill="#8C7A55" opacity=".6" />
    <rect x="78" y="94" width="16" height="38" fill={P.stone} />
    <rect x="78" y="94" width="16" height="4" fill="#8C7A55" />
    <rect x="202" y="112" width="66" height="20" fill="#E4D6B4" />
    <rect x="202" y="112" width="66" height="4" fill="#8C7A55" />
    <rect x="232" y="120" width="12" height="12" fill="#8C7A55" opacity=".6" />
  </>
);

/** Sunrise over the volcanic pinnacles of the Ahaggar. */
const assekremHoggar: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#F6C88A" to="#D97F4E" />
    <circle cx="150" cy="96" r="30" fill={P.gold} opacity=".9" />
    <path d="M0 132 L44 84 L74 116 L104 72 L142 132 Z" fill="#6B4630" opacity=".85" />
    <path d="M120 132 L158 78 L186 108 L214 62 L252 132 Z" fill="#4A2F22" opacity=".9" />
    <path d="M226 132 L262 90 L300 132 Z" fill="#3A2419" opacity=".85" />
    <rect y="130" width="300" height="50" fill="#2A1A13" />
    <rect y="130" width="300" height="4" fill={P.earthDark} opacity=".5" />
  </>
);

/** The avenue of ficus and palms, in perspective. */
const jardinEssaiHamma: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#E8F2E0" to="#C6DCBE" />
    <rect y="120" width="300" height="60" fill="#8FA87A" opacity=".5" />
    <path d="M118 180 L136 118 L164 118 L182 180 Z" fill={P.stoneMid} />
    <path d="M150 118 q-70 -14 -104 -60 M150 118 q70 -14 104 -60" stroke={P.greenDark} strokeWidth="3" fill="none" opacity=".45" />
    {[
      { x: 30, h: 74, s: 1.15 },
      { x: 268, h: 74, s: 1.15 },
      { x: 72, h: 58, s: 0.92 },
      { x: 226, h: 58, s: 0.92 },
      { x: 108, h: 44, s: 0.7 },
      { x: 192, h: 44, s: 0.7 },
    ].map((t) => (
      <Palm key={t.x} x={t.x} y={126} h={t.h} scale={t.s} />
    ))}
    <ellipse cx="150" cy="74" rx="52" ry="20" fill={P.greenDark} opacity=".25" />
  </>
);

/** The great mosque on the bay: a very tall square minaret beside the dome. */
const djamaaElDjazair: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#E9F1F3" to="#C8DDE0" />
    <rect y="146" width="300" height="34" fill={P.seaTop} />
    <rect y="162" width="300" height="18" fill={P.seaDeep} opacity=".5" />
    <rect y="140" width="300" height="8" fill={P.stoneMid} />
    <rect x="34" y="106" width="150" height="34" fill={P.white} />
    {[42, 74, 106, 138, 162].map((x) => (
      <path key={x} d={`M${x} 140 v-16 a9 9 0 0 1 18 0 v16 Z`} fill={P.green} opacity=".22" />
    ))}
    <path d="M74 106 a36 26 0 0 1 72 0 Z" fill={P.white} />
    <path d="M74 106 a36 26 0 0 1 72 0" fill="none" stroke={P.stoneMid} strokeWidth="2" />
    <rect x="106" y="66" width="8" height="14" fill={P.gold} rx="2" />
    {/* 265 m: the tallest minaret in the world, and the reason for this framing. */}
    <rect x="214" y="18" width="26" height="122" fill={P.white} />
    <rect x="210" y="14" width="34" height="7" fill={P.stoneMid} rx="1" />
    <rect x="219" y="26" width="16" height="7" fill={P.green} opacity=".25" rx="1" />
    <rect x="219" y="44" width="16" height="7" fill={P.green} opacity=".25" rx="1" />
    <rect x="219" y="62" width="16" height="7" fill={P.green} opacity=".25" rx="1" />
    <rect x="222" y="4" width="10" height="10" fill={P.gold} rx="2" />
  </>
);

/** The basilica on its cliff above the bay of Algiers. */
const notreDameAfrique: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#EDF1F5" to="#CBDCE6" />
    <rect y="150" width="300" height="30" fill={P.seaTop} />
    <rect y="164" width="300" height="16" fill={P.seaDeep} opacity=".55" />
    <path d="M0 150 L64 126 L236 126 L300 150 Z" fill={P.stoneDark} opacity=".65" />
    <rect x="86" y="86" width="128" height="40" fill="#F0E7D8" />
    <path d="M104 86 a46 34 0 0 1 92 0 Z" fill={P.white} />
    <path d="M104 86 a46 34 0 0 1 92 0" fill="none" stroke={P.stoneMid} strokeWidth="2" />
    <rect x="144" y="34" width="12" height="20" fill={P.white} />
    <path d="M150 26 L158 34 H142 Z" fill={P.gold} />
    <path d="M150 18 v10 M146 22 h8" stroke={P.stoneDark} strokeWidth="2" />
    {[96, 118, 140, 162, 184].map((x) => (
      <path key={x} d={`M${x} 126 v-18 a8 8 0 0 1 16 0 v18 Z`} fill={P.terracotta} opacity=".28" />
    ))}
    <rect x="70" y="100" width="16" height="26" fill={P.stone} />
    <rect x="214" y="100" width="16" height="26" fill={P.stone} />
  </>
);

/** The Rhumel gorge, and the bridge that answers it. */
const constantinePonts: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#EFEAE0" to="#D6CDBE" />
    <path d="M0 82 L96 82 L96 180 L0 180 Z" fill={P.stoneDark} />
    <path d="M204 82 L300 82 L300 180 L204 180 Z" fill={P.stoneDark} />
    <path d="M96 82 L120 128 L114 180 L96 180 Z" fill={P.earthDark} opacity=".35" />
    <path d="M204 82 L180 128 L186 180 L204 180 Z" fill={P.earthDark} opacity=".35" />
    {/* Houses crowding the very edge of the plateau. Terracotta roofs and a
        dark sill, or they vanish into a pale sky. */}
    {[
      { x: 4, y: 54, w: 26, h: 28 },
      { x: 32, y: 62, w: 24, h: 20 },
      { x: 58, y: 50, w: 26, h: 32 },
    ].map((b) => (
      <g key={b.x}>
        <rect x={b.x} y={b.y} width={b.w} height={b.h} fill="#F0E7D8" stroke="#9A8B6B" strokeWidth="1.2" />
        <rect x={b.x - 2} y={b.y - 5} width={b.w + 4} height="6" fill={P.terracotta} />
        <rect x={b.x + 7} y={b.y + 9} width="7" height="10" fill={P.night} opacity=".35" />
      </g>
    ))}
    {[
      { x: 216, y: 58, w: 24, h: 24 },
      { x: 242, y: 50, w: 26, h: 32 },
      { x: 270, y: 64, w: 24, h: 18 },
    ].map((b) => (
      <g key={b.x}>
        <rect x={b.x} y={b.y} width={b.w} height={b.h} fill="#F0E7D8" stroke="#9A8B6B" strokeWidth="1.2" />
        <rect x={b.x - 2} y={b.y - 5} width={b.w + 4} height="6" fill={P.terracotta} />
        <rect x={b.x + 7} y={b.y + 8} width="7" height="9" fill={P.night} opacity=".35" />
      </g>
    ))}
    {/* Sidi M'Cid: deck, towers, and the catenary between them. */}
    <rect x="88" y="74" width="124" height="5" fill={P.night} opacity=".8" />
    <rect x="94" y="34" width="5" height="44" fill={P.night} opacity=".85" />
    <rect x="201" y="34" width="5" height="44" fill={P.night} opacity=".85" />
    <path d="M96 36 Q150 74 203 36" fill="none" stroke={P.night} strokeWidth="2.4" opacity=".8" />
    {[112, 128, 144, 160, 176, 192].map((x) => (
      <line key={x} x1={x} y1="74" x2={x} y2={40 + Math.abs(150 - x) * 0.22} stroke={P.night} strokeWidth="1.1" opacity=".6" />
    ))}
  </>
);

/** The solitary minaret of Mansourah, and its great gate. */
const tlemcenMansourah: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#F4F1E2" to="#E2DFC4" />
    <path d="M0 112 L78 72 L156 112 Z" fill="#6E7F5C" opacity=".8" />
    <path d="M164 112 L246 76 L300 112 Z" fill="#5C6D4C" opacity=".85" />
    <rect y="140" width="300" height="40" fill="#9B9469" />
    <rect y="132" width="300" height="9" fill="#B6AD7D" />
    {/* One face of the minaret survived; the rest of the siege city did not. */}
    <rect x="118" y="24" width="62" height="108" fill="#DFC79A" />
    <rect x="118" y="24" width="10" height="108" fill="#EBD9B4" />
    <rect x="170" y="24" width="10" height="108" fill="#C9AF7E" />
    <rect x="113" y="17" width="72" height="8" fill="#C9AF7E" rx="1" />
    {/* The great arched opening that splits it. */}
    <path d="M132 132 V76 a17 17 0 0 1 34 0 v56 Z" fill="#6B5A3A" />
    <path d="M138 132 V78 a11 11 0 0 1 22 0 v54 Z" fill="#4C3F28" />
    <rect x="126" y="52" width="46" height="6" fill={P.terracotta} opacity=".65" />
    <rect x="126" y="38" width="46" height="6" fill={P.terracotta} opacity=".45" />
    <rect x="36" y="106" width="70" height="26" fill="#DFC79A" />
    <rect x="36" y="106" width="70" height="4" fill="#C9AF7E" />
    <rect x="92" y="92" width="14" height="40" fill="#EBD9B4" />
    <rect x="198" y="112" width="74" height="20" fill="#DFC79A" />
    <rect x="198" y="112" width="74" height="4" fill="#C9AF7E" />
  </>
);

/** The Spanish fort on the Murdjadjo ridge above the bay of Oran. */
const santaCruzOran: Scene = (uid) => (
  <>
    <Sky id={`${uid}s`} from="#EAF1F4" to="#C6DBE2" />
    <rect y="152" width="300" height="28" fill={P.seaTop} />
    <rect y="166" width="300" height="14" fill={P.seaDeep} opacity=".5" />
    <path d="M0 152 L86 74 L182 106 L300 152 Z" fill="#8C9A82" />
    <path d="M0 152 L86 74 L128 92 L60 152 Z" fill="#7B8A72" opacity=".8" />
    {/* Bastioned fort: curtain wall, corner towers, crenellations. */}
    <rect x="58" y="52" width="76" height="26" fill={P.stone} />
    <rect x="50" y="46" width="18" height="32" fill={P.stoneMid} />
    <rect x="126" y="46" width="18" height="32" fill={P.stoneMid} />
    {[52, 62, 72, 82, 92, 102, 112, 122, 132].map((x) => (
      <rect key={x} x={x} y="42" width="6" height="6" fill={P.stoneMid} />
    ))}
    <rect x="88" y="62" width="12" height="16" fill={P.night} opacity=".3" rx="1" />
    {/* The chapel below the fort. */}
    <rect x="176" y="112" width="30" height="18" fill={P.white} />
    <path d="M176 112 L191 100 L206 112 Z" fill="#F0E7D8" />
    <path d="M191 96 v-8 M187 92 h8" stroke={P.stoneDark} strokeWidth="2" />
  </>
);

const SITE_ART: Record<string, Scene> = {
  tipasa,
  timgad,
  djemila,
  "casbah-alger": casbahAlger,
  "vallee-mzab": valleeMzab,
  "tassili-najjer": tassiliNajjer,
  "qalaa-beni-hammad": qalaaBeniHammad,
  "assekrem-hoggar": assekremHoggar,
  "jardin-essai-hamma": jardinEssaiHamma,
  "djamaa-el-djazair": djamaaElDjazair,
  "notre-dame-afrique": notreDameAfrique,
  "constantine-ponts": constantinePonts,
  "tlemcen-mansourah": tlemcenMansourah,
  "santa-cruz-oran": santaCruzOran,
};

/** A site added to the catalogue without its own drawing still gets a fitting one. */
const CATEGORY_ART: Record<string, Scene> = {
  archaeological: tipasa,
  medina: casbahAlger,
  natural: tassiliNajjer,
  garden: jardinEssaiHamma,
  religious: notreDameAfrique,
  urban: constantinePonts,
  fortress: santaCruzOran,
};

export function SiteArt({
  slug,
  category,
  className = "",
}: {
  slug?: string;
  category?: string;
  className?: string;
}) {
  // Gradient ids must be unique per instance: several of these render side by
  // side, and duplicate ids make every card paint the first card's sky.
  const uid = `a${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const scene =
    (slug ? SITE_ART[slug] : undefined) ?? CATEGORY_ART[category ?? ""] ?? CATEGORY_ART.archaeological;

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
