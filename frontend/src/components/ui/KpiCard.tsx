import React from "react";
import { LucideIcon } from "lucide-react";

interface KpiCardProps {
    title: string;
    value: string;
    icon: LucideIcon;
    trend?: string;
    trendUp?: boolean;
    /** e.g. "vs previous period" or "of target" */
    trendSuffix?: string;
    /** Optional goal progress 0–100 */
    goalPct?: number;
    /** Shown under the progress bar, e.g. "Target ₹5.2 Cr" */
    targetLabel?: string;
    /** Stagger delay in ms for entrance animation */
    animationDelay?: number;
}

export function KpiCard({ title, value, icon: Icon, trend, trendUp, trendSuffix = "vs previous period", goalPct, targetLabel, animationDelay = 0 }: KpiCardProps) {
    return (
        <div
            className="bg-app-card border border-app-border rounded-xl p-6 shadow-sm flex flex-col justify-between animate-slide-up opacity-0 hover:border-app-border-strong transition-colors duration-200"
            style={{ animationDelay: `${animationDelay}ms` }}
        >
            <div className="flex justify-between items-start">
                <p className="text-sm font-medium text-app-fg-muted">{title}</p>
                <div className="p-2 rounded-lg bg-app-muted border border-app-border">
                    <Icon className="h-5 w-5 text-app-gold" />
                </div>
            </div>
            <div className="mt-4">
                <h3 className="text-2xl font-bold text-app-fg tracking-tight">{value}</h3>
                {trend != null && trend !== "" && (
                    <p className={`text-sm mt-1 flex items-center ${trendUp === true ? "text-green-600 dark:text-green-400" : trendUp === false ? "text-red-600 dark:text-red-400" : "text-app-fg-muted"}`}>
                        <span>{trendUp === true ? "↑" : trendUp === false ? "↓" : ""}</span>
                        <span className="ml-1">{trend} {trendSuffix}</span>
                    </p>
                )}
                {goalPct != null && (
                    <div className="mt-2">
                        {targetLabel && (
                            <p className="text-xs text-app-fg-muted mb-1">{targetLabel}</p>
                        )}
                        <div className="h-1.5 bg-app-border-strong rounded-full overflow-hidden">
                            <div
                                className="h-full bg-app-gold rounded-full transition-all"
                                style={{ width: `${Math.min(100, Math.max(0, goalPct))}%` }}
                            />
                        </div>
                        <p className="text-xs text-app-fg-muted mt-1">{Math.round(Math.min(100, Math.max(0, goalPct)))}% of target</p>
                    </div>
                )}
            </div>
        </div>
    );
}
