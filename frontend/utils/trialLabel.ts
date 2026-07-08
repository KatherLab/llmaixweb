/**
 * Display label for a trial, preferring a user-set name and falling back to the
 * per-project sequence number ("Trial #N") — never the global DB id.
 *
 * The `fallbackId` is only used when the trial object is missing or predates
 * the `project_trial_number` column (e.g. a stale cached object mid-deploy);
 * in that degraded case we fall back to the id rather than show nothing.
 *
 * @param trial trial-like object (Trial, TrialSummary, or WS payload slice)
 * @param fallbackId id to use if no name and no project_trial_number
 */
export function trialLabel(
  trial:
    | {
        name?: string | null
        project_trial_number?: number | null
      }
    | null
    | undefined,
  fallbackId?: number,
): string {
  const name = trial?.name
  if (name && name.trim().length > 0) return name
  if (trial?.project_trial_number) return `Trial #${trial.project_trial_number}`
  return fallbackId != null ? `Trial #${fallbackId}` : 'Trial'
}
