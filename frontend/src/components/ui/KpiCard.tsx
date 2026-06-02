import React from "react";
import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

interface KpiCardProps {
    title: string;
    value: string;
    icon: LucideIcon;
    trend?: string;
    trendUp?: boolean;
    trendSuffix?: string;
    goalPct?: number;
    targetLabel?: string;
    animationDelay?: number;
    sparklineData?: number[];
}

export function KpiCard({
    title,
    value,
    icon: Icon,
    trend,
    trendUp,
    trendSuffix = "vs previous period",
    goalPct,
    targetLabel,
    animationDelay = 0,
    sparklineData,
}: KpiCardProps) {
    const sparkPoints = sparklineData?.map(v => ({ v })) ?? [];
    const hasTrend = trend != null && trend !== "";
    const isPositive = trendUp === true;
    const isNegative = trendUp === false;

    return (
        <div
            className="relative bg-app-card border border-app-border rounded-xl p-5 shadow-sm flex flex-col justify-between
                       animate-slide-up opacity-0 hover:border-app-border-strong hover:shadow-md
                       transition-all duration-200 overflow-hidden group"
            style={{ animationDelay: `${animationDelay}ms` }}
        >
            {/* Subtle gold glow on hover */}
            <div className="absolute inset-0 bg-app-gold/0 group-hover:bg-app-gold/[0.02] transition-colors duration-300 pointer-events-none rounded-xl" />

            {/* Header row */}
            <div className="flex justify-between items-start">
                <p className="text-xs font-semibold text-app-fg-muted uppercase tracking-wide leading-snug">{title}</p>
                <div className="p-2 rounded-lg bg-app-muted border border-app-border shrink-0 ml-2">
                    <Icon className="h-4 w-4 text-app-gold" />
                </div>
            </div>

            {/* Value */}
            <div className="mt-3">
                <h3 className="text-3xl font-bold text-app-fg tracking-tight tabular-nums leading-none">{value}</h3>

                {/* Trend */}
                {hasTrend && (
                    <div className={`flex items-center gap-1 mt-2 text-xs font-medium
                        ${isPositive ? "text-emerald-400" : isNegative ? "text-red-400" : "text-app-fg-muted"}`}>
                        {isPositive && <TrendingUp className="h-3.5 w-3.5 shrink-0" />}
                        {isNegative && <TrendingDown className="h-3.5 w-3.5 shrink-0" />}
                        <span>{trend} {trendSuffix}</span>
                    </div>
                )}

                {/* Goal progress */}
                {goalPct != null && (
                    <div className="mt-3">
                        {targetLabel && (
                            <p className="text-[10px] text-app-fg-muted mb-1.5 font-medium">{targetLabel}</p>
                        )}
                        <div className="h-1.5 bg-app-border-strong rounded-full overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-700
                                    ${goalPct >= 100 ? "bg-emerald-400" : goalPct >= 60 ? "bg-app-gold" : "bg-orange-400"}`}
                                style={{ width: `${Math.min(100, Math.max(0, goalPct))}%` }}
                            />
                        </div>
                        <p className="text-[10px] text-app-fg-muted mt-1">
                            {Math.round(Math.min(100, Math.max(0, goalPct)))}% of target
                        </p>
                    </div>
                )}
            </div>

            {/* Sparkline — bottom of card, no axes */}
            {sparkPoints.length > 1 && (
                <div className="absolute bottom-0 left-0 right-0 h-10 opacity-30 group-hover:opacity-50 transition-opacity">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={sparkPoints} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                            <defs>
                                <linearGradient id={`spark-${title}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="var(--app-gold)" stopOpacity={0.5} />
                                    <stop offset="95%" stopColor="var(--app-gold)" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <Area type="monotone" dataKey="v" stroke="var(--app-gold)" strokeWidth={1.5} fill={`url(#spark-${title})`} dot={false} isAnimationActive={false} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}
