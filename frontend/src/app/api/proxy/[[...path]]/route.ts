import { NextRequest, NextResponse } from "next/server";

const BACKEND = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").trim().replace(/\/+$/, "");

export async function GET(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
    try {
        return await proxy(request, context, "GET");
    } catch (e) {
        return NextResponse.json({ error: "Proxy error", message: String(e) }, { status: 500 });
    }
}

export async function POST(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
    try {
        return await proxy(request, context, "POST");
    } catch (e) {
        return NextResponse.json({ error: "Proxy error", message: String(e) }, { status: 500 });
    }
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
    try {
        return await proxy(request, context, "PUT");
    } catch (e) {
        return NextResponse.json({ error: "Proxy error", message: String(e) }, { status: 500 });
    }
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
    try {
        return await proxy(request, context, "DELETE");
    } catch (e) {
        return NextResponse.json({ error: "Proxy error", message: String(e) }, { status: 500 });
    }
}

export async function OPTIONS() {
    return new NextResponse(null, { status: 204, headers: { "Access-Control-Allow-Origin": "*" } });
}

async function proxy(
    request: NextRequest,
    context: { params: Promise<{ path?: string[] }> },
    method: string
): Promise<NextResponse> {
    try {
        const { path = [] } = await context.params;
        const pathStr = path.length ? path.join("/") : "";
        const search = request.nextUrl.searchParams.toString();
        const url = `${BACKEND}/${pathStr}${search ? `?${search}` : ""}`;

        if (!BACKEND || BACKEND.startsWith("/")) {
            return NextResponse.json({ error: "Backend URL not configured (set NEXT_PUBLIC_API_URL)" }, { status: 502 });
        }

        const headers = new Headers();
        request.headers.forEach((v, k) => {
            if (k.toLowerCase() === "host" || k.toLowerCase() === "connection") return;
            headers.set(k, v);
        });

        const init: RequestInit = { method, headers };
        if (method !== "GET" && method !== "HEAD") {
            const contentType = request.headers.get("content-type");
            if (contentType?.includes("application/json")) {
                init.body = await request.text();
            } else if (contentType?.includes("multipart/form-data")) {
                init.body = await request.arrayBuffer();
                headers.set("content-type", contentType);
            }
        }

        // 55s timeout so cold-start backends (e.g. Render) can respond without hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 55000);
        const res = await fetch(url, { ...init, signal: controller.signal }).finally(() => clearTimeout(timeoutId));
        const resHeaders = new Headers();
        res.headers.forEach((v, k) => {
            const lower = k.toLowerCase();
            if (lower === "content-encoding" || lower === "transfer-encoding") return;
            resHeaders.set(k, v);
        });
        resHeaders.set("Access-Control-Allow-Origin", "*");
        resHeaders.set("Content-Encoding", "identity");

        const body = res.status === 204 || res.status === 304 ? null : await res.text();
        if (body !== null) {
            const bytes = new TextEncoder().encode(body);
            resHeaders.set("Content-Length", String(bytes.length));
            return new NextResponse(bytes, { status: res.status, statusText: res.statusText, headers: resHeaders });
        }
        return new NextResponse(null, { status: res.status, statusText: res.statusText, headers: resHeaders });
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        console.error("[proxy]", message, e);
        return NextResponse.json({ error: "Backend unreachable", message }, { status: 502 });
    }
}
