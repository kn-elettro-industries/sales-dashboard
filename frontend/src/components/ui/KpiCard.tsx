import React from "react";
import { LucideIcon } from "lucide-react";

interface KpiCardProps {
    title: string;
    value: string;
    icon: LucideIcon;
    trend?: string;
    trendUp?: boolean;
}

export function KpiCard({ title, value, icon: Icon, trend, trendUp }: KpiCardProps) {
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
                {trend && (
                    <p className={`text-sm mt-1 flex items-center ${trendUp ? 'text-green-400' : 'text-red-400'}`}>
                        <span>{trendUp ? '↑' : '↓'}</span>
                        <span className="ml-1">{trend} from last month</span>
                    </p>
                )}
            </div>
        </div>
    );
}
