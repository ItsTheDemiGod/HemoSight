/* The session's working state, kept in localStorage so a reload does not lose the
   submission you just uploaded. Deliberately not a state library: three ids and a
   check selection do not need one. */

const KEY = "hemosight-audit-session";

export interface SessionState {
  submissionId?: string;
  preregId?: string;
  runId?: string;
  checks?: string[];
}

export function readSession(): SessionState {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}") as SessionState;
  } catch {
    return {};
  }
}

export function writeSession(patch: SessionState): SessionState {
  const next = { ...readSession(), ...patch };
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* private browsing: the app still works, it just forgets on reload */
  }
  return next;
}
