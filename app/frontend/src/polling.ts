/* Polling a background job, as a plain async function rather than an effect.
 *
 * WHY THIS IS NOT A setInterval IN A useEffect ANY MORE. The first version was, and
 * measurement (tools/measure_poll_failure.mjs) found two defects that the happy path
 * never exercises:
 *
 *   - When the backend stopped answering, `await api.run(id)` rejected inside the
 *     interval callback. Nothing caught it, so the interval kept firing every 706 ms
 *     indefinitely, producing an uncaught "TypeError: Failed to fetch" per tick - 34 of
 *     them in 12 seconds - while the interface went on showing a progress bar. A poll
 *     loop with no terminating condition is the exact class of bug this audit was
 *     looking for.
 *   - When the backend answered slowly, setInterval did not wait for the request it had
 *     already issued, so polls stacked: 5 concurrent requests against a 3-second
 *     response, growing with latency.
 *
 * Both are structural, and both disappear if the loop schedules the NEXT request only
 * after the previous one has settled. That is what this does. Being a plain function it
 * is also directly testable, which an effect is not without a DOM test harness.
 */

export type JobStatus = "queued" | "running" | "done" | "error";

export interface Pollable {
  id: string;
  status: JobStatus;
}

export interface PollOptions<T extends Pollable> {
  /** Fetch the current job state. May reject. */
  fetchJob: () => Promise<T>;
  /** Called with every successful reading, including the final one. */
  onUpdate: (job: T) => void;
  /** Called once, if polling gives up before the job settles. */
  onGiveUp?: (message: string) => void;
  /** Base delay between attempts. */
  intervalMs?: number;
  /** Consecutive failures tolerated before giving up. */
  maxConsecutiveFailures?: number;
  /** Injected for tests; defaults to a real timer. */
  sleep?: (ms: number) => Promise<void>;
}

export interface PollHandle {
  /** Stop polling. Safe to call repeatedly, and after the job has settled. */
  cancel: () => void;
  /** Resolves when polling has stopped, for whatever reason. */
  finished: Promise<void>;
}

const realSleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export const isSettled = (s: JobStatus): boolean => s === "done" || s === "error";

/**
 * Poll until the job settles, the caller cancels, or the backend fails repeatedly.
 *
 * Exactly one request is ever in flight. Failures back off linearly and are counted;
 * a run of them ends the loop through onGiveUp rather than continuing forever.
 */
export function pollUntilSettled<T extends Pollable>(opts: PollOptions<T>): PollHandle {
  const {
    fetchJob, onUpdate, onGiveUp,
    intervalMs = 700,
    maxConsecutiveFailures = 5,
    sleep = realSleep,
  } = opts;

  let cancelled = false;
  let failures = 0;

  const finished = (async () => {
    while (!cancelled) {
      let job: T;
      try {
        job = await fetchJob();
        failures = 0;
      } catch (err) {
        failures += 1;
        if (cancelled) return;
        if (failures >= maxConsecutiveFailures) {
          onGiveUp?.(
            `the server stopped responding after ${failures} attempts: ` +
            `${err instanceof Error ? err.message : String(err)}`);
          return;
        }
        // Linear back-off: a server that is down does not need to be asked 85 times a
        // minute, and the request that eventually succeeds is not made sooner by it.
        await sleep(intervalMs * failures);
        continue;
      }

      if (cancelled) return;        // unmounted while the request was in flight
      onUpdate(job);
      if (isSettled(job.status)) return;
      await sleep(intervalMs);
    }
  })();

  return { cancel: () => { cancelled = true; }, finished };
}
