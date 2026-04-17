"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/ThemeContext";

/** Fixed control for auth pages (no sidebar). */
export function ThemeCornerToggle() {
    const { theme, toggleTheme, mounted } = useTheme();
    return (
        <button
            type="button"
            onClick={toggleTheme}
            className="fixed top-4 right-4 z-50 flex h-10 w-10 items-center justify-center rounded-lg border border-app-border bg-app-card text-app-gold shadow-md transition-colors hover:border-app-gold/40 hover:bg-app-hover"
            title={theme === "dark" ? "Light mode" : "Dark mode"}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
            {!mounted ? <Moon className="h-5 w-5 opacity-60" /> : theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
    );
}
