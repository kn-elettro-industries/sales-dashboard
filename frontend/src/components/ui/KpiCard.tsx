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
}

export function KpiCard({ title, value, icon: Icon, trend, trendUp, trendSuffix = "vs previous period", goalPct }: KpiCardProps) {
    return (
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 shadow-sm flex flex-col justify-between">
            <div className="flex justify-between items-start">
                <p className="text-sm font-medium text-gray-400">{title}</p>
                <div className="p-2 bg-[#2d333b] rounded-lg">
                    <Icon className="h-5 w-5 text-[#daa520]" />
                </div>
            </div>
            <div className="mt-4">
                <h3 className="text-2xl font-bold text-white tracking-tight">{value}</h3>
                {trend != null && trend !== "" && (
                    <p className={`text-sm mt-1 flex items-center ${trendUp === true ? "text-green-400" : trendUp === false ? "text-red-400" : "text-gray-400"}`}>
                        <span>{trendUp === true ? "↑" : trendUp === false ? "↓" : ""}</span>
                        <span className="ml-1">{trend} {trendSuffix}</span>
                    </p>
                )}
                {goalPct != null && (
                    <div className="mt-2 h-1.5 bg-[#30363d] rounded-full overflow-hidden">
                        <div
                            className="h-full bg-[#daa520] rounded-full transition-all"
                            style={{ width: `${Math.min(100, Math.max(0, goalPct))}%` }}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
