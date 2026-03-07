"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

export function ClientKeyboardShortcuts() {
    const router = useRouter();
    const keyRef = useRef<string | null>(null);

    useEffect(() => {
        const handle = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
            if (e.key === "g" && !keyRef.current) {
                keyRef.current = "g";
                return;
            }
            if (keyRef.current === "g" && e.key === "r") {
                router.push("/reports");
                keyRef.current = null;
                return;
            }
            if (e.key === "Escape" || e.key === "g") keyRef.current = null;
        };
        window.addEventListener("keydown", handle);
        return () => window.removeEventListener("keydown", handle);
    }, [router]);

    return null;
}
