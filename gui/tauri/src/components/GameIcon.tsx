import type { CSSProperties } from "react";

import dotplotIcon from "../assets/game-icons/dotplot.svg";
import environmentIcon from "../assets/game-icons/environment.svg";
import karyotypeIcon from "../assets/game-icons/karyotype.svg";
import localIcon from "../assets/game-icons/local.svg";
import multiSpeciesIcon from "../assets/game-icons/multi-species.svg";
import orthologIcon from "../assets/game-icons/ortholog.svg";
import pairwiseIcon from "../assets/game-icons/pairwise.svg";

export type GameIconName =
  | "pairwise"
  | "multi-species"
  | "local"
  | "dotplot"
  | "karyotype"
  | "ortholog"
  | "environment";

const GAME_ICON_URLS: Record<GameIconName, string> = {
  pairwise: pairwiseIcon,
  "multi-species": multiSpeciesIcon,
  local: localIcon,
  dotplot: dotplotIcon,
  karyotype: karyotypeIcon,
  ortholog: orthologIcon,
  environment: environmentIcon,
};

interface GameIconProps {
  name: GameIconName;
  className?: string;
}

export function GameIcon({ name, className = "h-6 w-6" }: GameIconProps) {
  const iconUrl = GAME_ICON_URLS[name];
  const maskStyle = {
    WebkitMask: `url(${iconUrl}) center / contain no-repeat`,
    mask: `url(${iconUrl}) center / contain no-repeat`,
  } satisfies CSSProperties;

  return <span aria-hidden="true" className={`inline-block bg-current ${className}`} style={maskStyle} />;
}
