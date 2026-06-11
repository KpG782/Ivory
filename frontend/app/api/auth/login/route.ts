export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { checkCredentials, isDemoLoginEnabled, makeSetCookieHeader } from "../_auth";

const SESSION_MAX_AGE = 86_400; // 24 hours

export async function POST(request: Request) {
  let body: Record<string, unknown>;
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    return Response.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  // One-click demo login: no credentials cross the wire. The session cookie
  // is derived server-side from the configured credentials, so this still
  // requires AUTH_USERNAME / AUTH_PASSWORD to be set.
  if (body.demo === true) {
    if (!isDemoLoginEnabled()) {
      return Response.json({ error: "Demo login is not enabled." }, { status: 403 });
    }
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie": makeSetCookieHeader(SESSION_MAX_AGE),
      },
    });
  }

  const username = String(body.username ?? "").trim();
  const password = String(body.password ?? "");

  if (!username || !password) {
    return Response.json({ error: "Username and password are required." }, { status: 400 });
  }

  // Artificial delay to resist brute-force timing attacks.
  await new Promise<void>((resolve) => setTimeout(resolve, 150));

  if (!checkCredentials(username, password)) {
    return Response.json({ error: "Invalid username or password." }, { status: 401 });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Set-Cookie": makeSetCookieHeader(SESSION_MAX_AGE),
    },
  });
}
