export const dynamic = "force-dynamic";
export const runtime = "nodejs";

import { isValidSession } from "../auth/_auth";

const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000";

function buildBackendUrl(path: string): string {
  const base =
    process.env.BACKEND_API_BASE_URL?.trim() || DEFAULT_BACKEND_BASE_URL;
  return `${base.replace(/\/$/, "")}${path}`;
}

export async function POST(request: Request) {
  // Session resets are workspace actions — require the same httpOnly session
  // cookie that /api/auth/check validates before proxying to the backend.
  if (!isValidSession(request.headers.get("cookie"))) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const payload = await request.text();
  const upstream = await fetch(buildBackendUrl("/reset"), {
    method: "POST",
    headers: {
      "Content-Type": request.headers.get("content-type") || "application/json",
      Accept: request.headers.get("accept") || "application/json"
    },
    cache: "no-store",
    body: payload
  });

  const headers = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  return new Response(await upstream.text(), {
    status: upstream.status,
    statusText: upstream.statusText,
    headers
  });
}
