/**
 * Client-side auth helpers.
 *
 * Authentication is now handled server-side via httpOnly cookies.
 * Credentials (AUTH_USERNAME / AUTH_PASSWORD) live in server-side env vars
 * and are never bundled into client JavaScript.
 *
 * The only thing exposed to the browser is an optional demo username hint
 * (NEXT_PUBLIC_AUTH_DEMO_USER) so reviewers know what to type in the
 * username field.  The password is intentionally not exposed.
 */

export const AUTH_COOKIE_NAME = "ivory_session";

/** Optional username hint shown on the login screen for demo environments. */
export function getDemoUsernameHint(): string {
  return process.env.NEXT_PUBLIC_AUTH_DEMO_USER || "";
}

/** POST /api/auth/login — returns true on success. */
export async function serverLogin(username: string, password: string): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) return { ok: true };
    const data = await res.json().catch(() => ({})) as { error?: string };
    return { ok: false, error: data.error || "Invalid username or password." };
  } catch {
    return { ok: false, error: "Login failed. Please check your connection." };
  }
}

/** POST /api/auth/logout — clears the httpOnly session cookie. */
export async function serverLogout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
}

/** GET /api/auth/check — returns true if the session cookie is valid. */
export async function checkAuthStatus(): Promise<boolean> {
  try {
    const res = await fetch("/api/auth/check", { cache: "no-store" });
    if (!res.ok) return false;
    const data = await res.json() as { authenticated?: boolean };
    return data.authenticated === true;
  } catch {
    return false;
  }
}
