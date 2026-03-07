import { NextRequest, NextResponse } from "next/server";

const BACKEND = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").trim().replace(/\/+$/, "");

export async function GET(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
    return proxy(request, context, "GET");
}

export async function POST(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
    return proxy(request, context, "POST");
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
    return proxy(request, context, "PUT");
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
    return proxy(request, context, "DELETE");
}

export async function OPTIONS() {
    return new NextResponse(null, { status: 204, headers: { "Access-Control-Allow-Origin": "*" } });
}

async function proxy(
    request: NextRequest,
    context: { params: Promise<{ path?: string[] }> },
    method: string
) {
    const { path = [] } = await context.params;
    const pathStr = path.length ? path.join("/") : "";
    const search = request.nextUrl.searchParams.toString();
    const url = `${BACKEND}/${pathStr}${search ? `?${search}` : ""}`;

    try {
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

        const res = await fetch(url, init);
        const resHeaders = new Headers(res.headers);
        resHeaders.set("Access-Control-Allow-Origin", "*");
        return new NextResponse(res.body, { status: res.status, statusText: res.statusText, headers: resHeaders });
    } catch (e) {
        console.error("[proxy]", url, e);
        return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
    }
}
