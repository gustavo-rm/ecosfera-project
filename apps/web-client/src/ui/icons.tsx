import type { CSSProperties } from "react";

/** Local icon set (no icon font, no CDN). 24×24, stroke-based. Shapes are a PROPOSAL for the product designer to review. */
const P: Record<string, string> = {
  thermometer: "M10 4a2 2 0 0 1 4 0v9.5a4.5 4.5 0 1 1-4 0zM12 9v8",
  oxygen: "M9 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8zM16 13.5c1.5-1.5 4-.6 4 1.2c0 1.6-2 2.3-4 4.3h4.2",
  ph: "M12 3c3.5 4.5 6 7.5 6 11a6 6 0 0 1-12 0c0-3.500 2.500-6.500 6-11zM9.500 15h5",
  leaf: "M5 19c0-9 5-14 15-14c0 10-5 15-14 15M5 19c3-5 6-8 10-10",
  spark: "M12 3l2.200 5.800L20 11l-5.800 2.200L12 19l-2.200-5.800L4 11l5.800-2.200z",
  play: "M7 5l12 7l-12 7z", pause: "M7 5v14M17 5v14", forward: "M5 5l8 7l-8 7zM13 5l8 7l-8 7z", skip: "M5 5l10 7l-10 7zM19 5v14",
  layers: "M12 3l9 5l-9 5l-9-5zM3 13l9 5l9-5M3 17l9 5l9-5",
  chart: "M4 20V4M4 20h16M7 15l4-5l3 3l5-7", chat: "M4 5h16v11H9l-5 4z", target: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0-10 0M12 12h.010",
  flask: "M9 3h6M10 3v6l-5.500 9a2 2 0 0 0 1.700 3h11.600a2 2 0 0 0 1.700-3L14 9V3M7.500 15h9",
  book: "M4 5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2zM4 21V5M9 7h7",
  globe: "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18",
  settings: "M12 9a3 3 0 1 0 0 6a3 3 0 0 0 0-6zM4 12h2M18 12h2M12 4v2M12 18v2M6.300 6.300l1.500 1.500M16.200 16.200l1.500 1.500M17.700 6.300l-1.500 1.500M7.800 16.200l-1.500 1.500",
  close: "M6 6l12 12M18 6L6 18", check: "M5 12.500l4.500 4.500L19 7", alert: "M12 3l10 18H2zM12 10v5M12 18h.010", info: "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM12 11v6M12 7.500h.010",
  lock: "M6 11h12v9H6zM8.500 11V8a3.500 3.500 0 0 1 7 0v3", plus: "M12 5v14M5 12h14", minus: "M5 12h14", home: "M4 11l8-7l8 7v9h-5v-6H9v6H4z",
  up: "M12 19V5M6 11l6-6l6 6", down: "M12 5v14M6 13l6 6l6-6", flat: "M4 12h16M15 7l5 5l-5 5", eye: "M2 12c3-5.500 6.500-8 10-8s7 2.500 10 8c-3 5.500-6.500 8-10 8s-7-2.500-10-8zM12 9a3 3 0 1 0 0 6a3 3 0 0 0 0-6z",
  fire: "M12 3c1 4 5 5.500 5 10.500a5 5 0 0 1-10 0c0-2 1-3.500 2-4.500c.500 2 1.500 2.500 2 2.500c0-3 0-5 1-8.500z",
  drought: "M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8zM12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2",
  storm: "M7 16a4 4 0 0 1 .500-8a5.500 5.500 0 0 1 10.500 1.500a3.300 3.300 0 0 1 0 6.500M13 12l-3 5h4l-2 4",
  glaciation: "M12 2v20M3.500 7l17 10M20.500 7l-17 10M9 4l3 3l3-3M9 20l3-3l3 3", volcanism: "M3 20l6-10h6l6 10zM10 10l1-3M14 10l-1-3M12 3v2M8 5l1 1M16 5l-1 1",
  impact: "M20 4L9 15M20 4l-5 1M20 4l-1 5M7 14a3.500 3.500 0 1 0 3.500 3.500M3 21h18", eutrophication: "M3 9c3-3 6 3 9 0s6 3 9 0M3 14c3-3 6 3 9 0s6 3 9 0M3 19c3-3 6 3 9 0s6 3 9 0",
  pandemic: "M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8zM12 3v5M12 16v5M3 12h5M16 12h5M5.500 5.500l3.500 3.500M15 15l3.500 3.500M18.500 5.500L15 9M9 15l-3.500 3.500", invasive: "M3 12h11M10 7l5 5l-5 5M17 4h4v16h-4",
  users: "M9 11a3.500 3.500 0 1 0 0-7a3.500 3.500 0 0 0 0 7zM2 20c0-4 3-6 7-6s7 2 7 6M16 4.500a3.500 3.500 0 0 1 0 6.500M18 14c2.500.600 4 2.500 4 6", user: "M12 12a4 4 0 1 0 0-8a4 4 0 0 0 0 8zM4 21c0-4.500 3.500-7 8-7s8 2.500 8 7",
  download: "M12 3v12M7 10l5 5l5-5M4 20h16", send: "M3 11l18-8l-7 18l-3-7z", shield: "M12 3l8 3v6c0 5-3.500 8-8 9c-4.500-1-8-4-8-9V6z", clock: "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM12 7v5l3.500 2",
  search: "M11 4a7 7 0 1 0 0 14a7 7 0 0 0 0-14zM16 16l5 5", tree: "M12 21v-7M12 14c-4 0-7-2-7-5s2-4 3-4c.500-2 2-3 4-3s3.500 1 4 3c1 0 3 1 3 4s-3 5-7 5z", mountain: "M2 20l7-12l4 6l2-3l7 9z",
  water: "M12 3c3.500 4.500 6 7.500 6 11a6 6 0 0 1-12 0c0-3.500 2.500-6.500 6-11z", bolt: "M13 2L5 14h6l-1 8l8-12h-6z", coin: "M12 4a8 8 0 1 0 0 16a8 8 0 0 0 0-16zM12 8v8M9.500 10h4a1.500 1.500 0 0 1 0 3h-3a1.500 1.500 0 0 0 0 3h4",
  star: "M12 3l2.700 5.800l6.300.700l-4.700 4.300l1.300 6.200L12 16.900L6.400 20l1.300-6.200L3 9.500l6.300-.700z", table: "M3 5h18v14H3zM3 10h18M3 15h18M9 5v14", keyboard: "M3 7h18v10H3zM7 11h.010M11 11h.010M15 11h.010M7 14h10",
  text: "M5 6h14M5 10h14M5 14h9M5 18h11", moon: "M20 14.500A8 8 0 0 1 9.500 4a8 8 0 1 0 10.500 10.500z", sun: "M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8zM12 2v3M12 19v3M2 12h3M19 12h3",
  contrast: "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM12 3v18M12 7l5 2M12 12l7 1M12 17l5-1", reset: "M4 12a8 8 0 1 0 2.500-5.800M4 4v5h5", question: "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM9.500 9.500a2.500 2.500 0 1 1 3.500 2.300c-.700.400-1 .900-1 1.700M12 17h.010",
  seed: "M12 21c-4-3-6-6-6-10a6 6 0 0 1 12 0c0 4-2 7-6 10zM12 21V10", edit: "M4 20h4L19 9l-4-4L4 16zM13 7l4 4", trash: "M5 7h14M9 7V4h6v3M7 7l1 13h8l1-13",
  compare: "M12 3v18M4 7h5M4 12h5M4 17h5M15 7h5M15 12h5M15 17h5", microscope: "M9 3l4 7l-2 1l-4-7zM12 11a6 6 0 0 1 4 10H6M4 21h16M8 15h4",
  dna: "M7 3c0 5 10 5 10 9s-10 4-10 9M17 3c0 5-10 5-10 9s10 4 10 9M8 7h8M8 17h8", cycle: "M4 12a8 8 0 0 1 14-5l2-2v6h-6l2-2a5 5 0 0 0-9 3M20 12a8 8 0 0 1-14 5l-2 2v-6h6l-2 2a5 5 0 0 0 9-3",
  web: "M5 6a2 2 0 1 0 0-.010M19 6a2 2 0 1 0 0-.010M12 12a2 2 0 1 0 0-.010M6 19a2 2 0 1 0 0-.010M18 19a2 2 0 1 0 0-.010M6.500 7.500l4 3.500M17.500 7.500l-4 3.500M11 13.500l-4 4M13 13.500l4 4",
  pyramid: "M12 3l9 17H3zM7.500 12h9M5.300 16h13.400", telescope: "M3 9l12-5l2 5l-12 5zM9 12l-3 9M12 11l4 10M17 6l4-1.500", flag: "M5 21V4M5 4h13l-3 4.500l3 4.500H5",
  menu: "M4 6h16M4 12h16M4 18h16", grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z", wind: "M3 8h10a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h7a2.500 2.500 0 1 1-2.500 2.500",
  footprint: "M8 4c2 0 3 2 3 5s-1 5-3 5s-3-2-3-5s1-5 3-5zM16 10c2 0 3 2 3 5s-1 5-3 5s-3-2-3-5s1-5 3-5z", bone: "M6 6l12 12M4.500 7.500a2 2 0 1 1 3-3M19.500 16.500a2 2 0 1 1-3 3",
};
export type IconName = keyof typeof P;
export const ICON_NAMES = Object.keys(P);

export function Icon({ name, size = 20, className, style, title }: { name: string; size?: number; className?: string; style?: CSSProperties; title?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className} style={{ flex: "none", ...style }} aria-hidden={title ? undefined : true} role={title ? "img" : undefined} aria-label={title} focusable="false">
      <path d={P[name] ?? P.info} />
    </svg>
  );
}
