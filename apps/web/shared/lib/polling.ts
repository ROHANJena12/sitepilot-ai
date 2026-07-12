/**
 * Shared adaptive poll intervals for audit + AI job polling.
 * Stops immediately when ``done`` is true.
 */
export function adaptivePollIntervalMs(
  attempt: number,
  done: boolean,
): number | false {
  if (done) return false;
  if (attempt < 6) return 500;
  if (attempt < 20) return 1000;
  return 2000;
}
