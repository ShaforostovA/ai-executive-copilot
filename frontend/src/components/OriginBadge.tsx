import type { DataOrigin } from "../types";

export function OriginBadge({ origin }: { origin: DataOrigin }) {
  return <span className={`badge badge-${origin.toLowerCase()}`}>{origin}</span>;
}
