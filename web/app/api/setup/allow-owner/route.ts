import type { NextRequest } from "next/server";

const API_BASE = process.env.AETHER_API_BASE ?? "http://127.0.0.1:8457";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const r = await fetch(`${API_BASE}/setup/allow_owner`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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