"use client";

import { useState, useEffect } from "react";
import { X, Lightbulb } from "lucide-react";

const DISMISS_KEY = "elettro_onboarding_dismissed";

export function OnboardingBanner() {
    const [show, setShow] = useState(false);

    useEffect(() => {
        try {
            if (!localStorage.getItem(DISMISS_KEY)) setShow(true);
        } catch {
            // ignore
        }
    }, []);

    const dismiss = () => {
        try {
            localStorage.setItem(DISMISS_KEY, "1");
        } catch {
            // ignore
        }
        setShow(false);
    };

    if (!show) return null;

    return (
        <div className="bg-[#2a2414] border-b border-[#daa520]/30 px-4 py-2 flex items-center justify-between gap-4 text-sm text-gray-200">
            <div className="flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-[#daa520] shrink-0" />
                <span>
                    First time? Use <strong className="text-[#daa520]">Filters</strong> above to narrow data, then open <strong className="text-[#daa520]">Reports</strong> to download PDFs. Press <kbd className="px-1.5 py-0.5 rounded bg-[#0d1117] text-[#daa520] font-mono text-xs">G</kbd> then <kbd className="px-1.5 py-0.5 rounded bg-[#0d1117] text-[#daa520] font-mono text-xs">R</kbd> to jump to Reports.
                </span>
            </div>
            <button type="button" onClick={dismiss} className="p-1 rounded hover:bg-[#30363d] text-gray-400 hover:text-white" aria-label="Dismiss">
                <X className="h-4 w-4" />
            </button>
        </div>
    );
}
