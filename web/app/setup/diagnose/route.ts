import type { NextRequest } from "next/server";

const API_BASE = process.env.AETHER_API_BASE ?? "http://127.0.0.1:8457";

export async function GET(_req: NextRequest) {
  try {
    const r = await fetch(`${API_BASE}/setup/diagnose`, {
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    const body = await r.json();
    return Response.json(body, { status: r.status });
  } catch (err) {
    return Response.json(
      {
        ok: false,
        error: "aether-api unreachable",
        detail: String(err),
      },
      { status: 502 }
    );
  }
}