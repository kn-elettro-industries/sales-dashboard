"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";

interface State {
    hasError: boolean;
    message: string;
}

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
    constructor(props: { children: React.ReactNode }) {
        super(props);
        this.state = { hasError: false, message: "" };
    }

    static getDerivedStateFromError(error: unknown): State {
        return { hasError: true, message: error instanceof Error ? error.message : String(error) };
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4 p-8">
                    <AlertTriangle className="w-12 h-12 text-red-400" />
                    <h2 className="text-lg font-semibold text-app-fg">Something went wrong</h2>
                    <p className="text-sm text-app-fg-muted max-w-md text-center">{this.state.message || "An unexpected error occurred on this page."}</p>
                    <button
                        onClick={() => this.setState({ hasError: false, message: "" })}
                        className="px-4 py-2 rounded-lg bg-app-gold text-app-on-gold text-sm font-medium hover:opacity-90"
                    >
                        Try again
                    </button>
                </div>
            );
        }
        return this.props.children;
    }
}
