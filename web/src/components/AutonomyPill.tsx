import { AUTONOMY_LABEL } from "../format";
import type { Autonomy } from "../types";

interface Props {
  level: Autonomy;
  simulated: boolean;
}

export function AutonomyPill({ level, simulated }: Props) {
  const note =
    level === "auto" && simulated ? "Auto: would auto-send. Simulated, nothing is sent." : undefined;
  return (
    <span className={`pill pill--${level}`} aria-label={note} title={note}>
      {AUTONOMY_LABEL[level]}
    </span>
  );
}
