import { NextRequest, NextResponse } from "next/server";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyToBackend(request, context, "GET");
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyToBackend(request, context, "POST");
}

async function proxyToBackend(request: NextRequest, context: RouteContext, method: "GET" | "POST") {
  try {
    const target = await buildTargetUrl(request, context);
    const body = method === "POST" ? await request.text() : undefined;
    const response = await fetch(target, {
      method,
      body: body || undefined,
      cache: "no-store",
      headers: requestHeaders(request),
    });
    const payload = await readJson(response);

    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown voice backend proxy error.";
    const status = message.includes("CRUCIBLE_API_BASE_URL") ? 500 : 502;

    return NextResponse.json({ detail: message }, { status });
  }
}

async function buildTargetUrl(request: NextRequest, context: RouteContext): Promise<URL> {
  const baseUrl = process.env.CRUCIBLE_API_BASE_URL;
  if (!baseUrl) {
    throw new Error("CRUCIBLE_API_BASE_URL is not configured for the voice proxy.");
  }

  const { path } = await context.params;
  const base = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const target = new URL(path.join("/"), base);
  target.search = request.nextUrl.search;
  return target;
}

function requestHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  return headers;
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return {};

  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}
