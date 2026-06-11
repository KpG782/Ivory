/**
 * Server-side auth helpers shared across /api/auth/* route handlers.
 *
 * Credentials are read from server-side env vars (AUTH_USERNAME / AUTH_PASSWORD).
 * They are never exposed to the browser — no NEXT_PUBLIC_ prefix.
 *
 * The session token is an HMAC-SHA256 of the credentials.  This is stateless
 * (no server-side token store needed) and invalidates automatically when
 * credentials change.
 */

import crypto from "node:crypto";

const SESSION_COOKIE_NAME = "ivory_session";
const DEFAULT_SECRET = "ivory-dev-secret-change-in-production";

function authConfig(): {
  username: string;
  password: string;
  secret: string;
} | null {
  const username = process.env.AUTH_USERNAME?.trim() || "";
  const password = process.env.AUTH_PASSWORD?.trim() || "";
  const secret = process.env.SESSION_SECRET || DEFAULT_SECRET;

  if (!username || !password) {
    return null;
  }

  return { username, password, secret };
}

function hmacToken(): string {
  const config = authConfig();
  if (!config) return "";

  return crypto
    .createHmac("sha256", config.secret)
    .update(`${config.username}:${config.password}`)
    .digest("hex");
}

/** Return true if the cookie header contains a valid session token. */
export function isValidSession(cookieHeader: string | null): boolean {
  if (!cookieHeader) return false;
  if (!authConfig()) return false;
  const token = parseCookieValue(cookieHeader, SESSION_COOKIE_NAME);
  if (!token) return false;
  const expected = hmacToken();
  if (!expected) return false;
  try {
    // Use constant-time comparison to prevent timing attacks.
    return crypto.timingSafeEqual(
      Buffer.from(token, "hex"),
      Buffer.from(expected, "hex")
    );
  } catch {
    return false;
  }
}

/**
 * Demo login is allowed when the public flag is on AND real credentials are
 * configured (the session token is an HMAC of them, so they must exist).
 * The flag is NEXT_PUBLIC_ because the login screen also uses it to decide
 * whether to render the one-click demo button.
 */
export function isDemoLoginEnabled(): boolean {
  return (
    process.env.NEXT_PUBLIC_AUTH_DEMO_LOGIN === "true" && authConfig() !== null
  );
}

/** Validate a username/password pair against server-side env vars. */
export function checkCredentials(username: string, password: string): boolean {
  const config = authConfig();
  if (!config) return false;
  return username === config.username && password === config.password;
}

/** Build a Set-Cookie header value that sets a secure httpOnly session cookie. */
export function makeSetCookieHeader(maxAge: number): string {
  const token = hmacToken();
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${SESSION_COOKIE_NAME}=${token}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}

/** Build a Set-Cookie header value that clears the session cookie. */
export function makeClearCookieHeader(): string {
  return `${SESSION_COOKIE_NAME}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0`;
}

function parseCookieValue(header: string, name: string): string | null {
  for (const part of header.split(";")) {
    const eqIdx = part.indexOf("=");
    if (eqIdx === -1) continue;
    const key = part.slice(0, eqIdx).trim();
    if (key === name) {
      return part.slice(eqIdx + 1).trim();
    }
  }
  return null;
}
