import { describe, expect, it, vi } from "vitest";
import { isSettled, pollUntilSettled, type Pollable } from "./polling";

/* Regression cover for the two defects measured in the original setInterval version:
   a loop that never stopped when the backend failed, and overlapping requests when the
   backend was slow. Both are properties of the loop, so they are tested directly. */

const nap = () => Promise.resolve();      // no real waiting in tests

function job(status: Pollable["status"]): Pollable {
  return { id: "r1", status };
}

describe("pollUntilSettled", () => {
  it("stops as soon as the job is done, and reports the final state", async () => {
    const states: Pollable["status"][] = ["queued", "running", "running", "done"];
    const fetchJob = vi.fn(async () => job(states.shift() ?? "done"));
    const seen: string[] = [];

    const h = pollUntilSettled({ fetchJob, onUpdate: (j) => seen.push(j.status), sleep: nap });
    await h.finished;

    expect(seen).toEqual(["queued", "running", "running", "done"]);
    expect(fetchJob).toHaveBeenCalledTimes(4);
  });

  it("stops on an error status without being cancelled", async () => {
    const fetchJob = vi.fn(async () => job("error"));
    const h = pollUntilSettled({ fetchJob, onUpdate: () => {}, sleep: nap });
    await h.finished;
    expect(fetchJob).toHaveBeenCalledTimes(1);
  });

  it("gives up after repeated failures instead of retrying for ever", async () => {
    // The measured defect: 17 polls in 12 s against a dead backend, one uncaught
    // rejection each, and no end.
    const fetchJob = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    const gaveUp = vi.fn();

    const h = pollUntilSettled({
      fetchJob, onUpdate: () => {}, onGiveUp: gaveUp,
      maxConsecutiveFailures: 4, sleep: nap,
    });
    await h.finished;

    expect(fetchJob).toHaveBeenCalledTimes(4);
    expect(gaveUp).toHaveBeenCalledOnce();
    expect(gaveUp.mock.calls[0][0]).toMatch(/stopped responding after 4 attempts/);
  });

  it("recovers when a transient failure is followed by success", async () => {
    let n = 0;
    const fetchJob = vi.fn(async () => {
      n += 1;
      if (n <= 2) throw new Error("blip");
      return job(n >= 4 ? "done" : "running");
    });
    const gaveUp = vi.fn();

    const h = pollUntilSettled({
      fetchJob, onUpdate: () => {}, onGiveUp: gaveUp, maxConsecutiveFailures: 5,
      sleep: nap,
    });
    await h.finished;

    expect(gaveUp).not.toHaveBeenCalled();
    expect(fetchJob).toHaveBeenCalledTimes(4);
  });

  it("never has two requests in flight, however slow the backend is", async () => {
    let inFlight = 0;
    let maxInFlight = 0;
    let calls = 0;
    const fetchJob = async () => {
      inFlight += 1;
      maxInFlight = Math.max(maxInFlight, inFlight);
      await new Promise((r) => setTimeout(r, 5));     // slower than the interval
      inFlight -= 1;
      calls += 1;
      return job(calls >= 5 ? "done" : "running");
    };

    const h = pollUntilSettled({ fetchJob, onUpdate: () => {}, intervalMs: 1 });
    await h.finished;

    expect(maxInFlight).toBe(1);
  });

  it("stops immediately on cancel and does not report a late response", async () => {
    let resolve!: (j: Pollable) => void;
    const fetchJob = vi.fn(() => new Promise<Pollable>((r) => { resolve = r; }));
    const onUpdate = vi.fn();

    const h = pollUntilSettled({ fetchJob, onUpdate, sleep: nap });
    h.cancel();                       // the component unmounts mid-request
    resolve(job("running"));          // the response arrives afterwards
    await h.finished;

    expect(onUpdate).not.toHaveBeenCalled();
    expect(fetchJob).toHaveBeenCalledTimes(1);
  });

  it("cancel is idempotent and safe after the job has settled", async () => {
    const fetchJob = vi.fn(async () => job("done"));
    const h = pollUntilSettled({ fetchJob, onUpdate: () => {}, sleep: nap });
    await h.finished;
    h.cancel();
    h.cancel();
    expect(fetchJob).toHaveBeenCalledTimes(1);
  });

  it("knows which statuses are terminal", () => {
    expect(isSettled("done")).toBe(true);
    expect(isSettled("error")).toBe(true);
    expect(isSettled("queued")).toBe(false);
    expect(isSettled("running")).toBe(false);
  });
});
