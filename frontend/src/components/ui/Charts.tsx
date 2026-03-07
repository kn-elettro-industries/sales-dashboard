"use client";

import React, { useState } from "react";
import { formatAxisTick, formatTooltipAmount, formatAmount } from "@/lib/format";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart as RechartsPieChart,
    Pie,
    Cell,
    ScatterChart,
    Scatter,
    ZAxis,
    Treemap,
    BarChart as RechartsBarChart,
    Bar
} from "recharts";

// High-contrast segment colors — each slice clearly distinct (donut & treemap)
const SEGMENT_COLORS = [
    "#daa520", "#0ea5e9", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899",
    "#14b8a6", "#e11d48", "#6366f1", "#84cc16", "#f97316", "#06b6d4"
];
// Legacy alias for other charts
const COLORS = SEGMENT_COLORS;

// Wrapper so Recharts never gets width/height -1 (fixes console warning)
function ChartWrapper({ children, className = "min-h-[320px] w-full mt-4" }: { children: React.ReactNode; className?: string }) {
    return (
        <div className={className} style={{ minWidth: 0, minHeight: 320 }}>
            {children}
        </div>
    );
}

function ChartEmpty({ message = "No data to display" }: { message?: string }) {
    return (
        <div className="flex flex-col items-center justify-center h-[320px] w-full text-gray-500">
            <div className="text-sm">{message}</div>
        </div>
    );
}

// 1. Gradient Area Chart (Replaces basic bar/line charts for continuous trends)
export function GradientAreaChart({ data, xKey, yKey, formatCurrency = true }: { data: any[]; xKey: string; yKey: string; formatCurrency?: boolean }) {
    const hasData = Array.isArray(data) && data.length > 0;
    if (!hasData) return <ChartEmpty message="No trend data for the selected period" />;

    return (
        <ChartWrapper>
            <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={data} margin={{ top: 16, right: 24, left: 8, bottom: 8 }}>
                    <defs>
                        <linearGradient id="colorYKey" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#daa520" stopOpacity={0.9} />
                            <stop offset="95%" stopColor="#daa520" stopOpacity={0.08} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#30363d" vertical={false} opacity={0.8} />
                    <XAxis dataKey={xKey} stroke="#8b949e" tick={{ fill: "#8b949e", fontSize: 12 }} tickLine={false} axisLine={false} />
                    <YAxis
                        stroke="#8b949e"
                        tick={{ fill: "#8b949e", fontSize: 12 }}
                        tickLine={false}
                        axisLine={false}
                        width={48}
                        tickFormatter={(val) => formatCurrency ? formatAxisTick(val) : String(val)}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: "#161b22", border: "1px solid #30363d", color: "#fff", borderRadius: "8px", boxShadow: "0 4px 12px rgba(0,0,0,0.3)" }}
                        labelStyle={{ color: "#daa520" }}
                        formatter={(value: any) => [formatCurrency ? `₹ ${Number(value || 0).toLocaleString("en-IN")}` : value, "Revenue"]}
                    />
                    <Area type="monotone" dataKey={yKey} stroke="#daa520" strokeWidth={2.5} fillOpacity={1} fill="url(#colorYKey)" dot={false} activeDot={{ r: 5, fill: "#daa520", stroke: "#161b22", strokeWidth: 2 }} />
                </AreaChart>
            </ResponsiveContainer>
        </ChartWrapper>
    );
}

// 2. Top Material Groups Donut — clear segments, legend below with name + %
export function InteractiveDonutChart({ data, nameKey, valueKey }: { data: any[]; nameKey: string; valueKey: string }) {
    const [activeIndex, setActiveIndex] = useState<number | null>(null);
    const hasData = Array.isArray(data) && data.length > 0;
    const total = hasData ? data.reduce((s, d) => s + (Number(d[valueKey]) || 0), 0) : 0;
    const chartData = hasData
        ? data.map((d, i) => {
            const val = Number(d[valueKey]) || 0;
            const pct = total > 0 ? (val / total) * 100 : 0;
            return {
                ...d,
                [nameKey]: d[nameKey] || "Other",
                fill: SEGMENT_COLORS[i % SEGMENT_COLORS.length],
                _pct: pct,
            };
        })
        : [];

    if (!hasData) return <ChartEmpty message="No material group data" />;

    return (
        <ChartWrapper className="min-h-[380px] w-full mt-4">
            <div className="flex flex-col items-center w-full">
                <div className="relative w-full" style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height={260}>
                        <RechartsPieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                            <Pie
                                data={chartData}
                                cx="50%"
                                cy="50%"
                                innerRadius={64}
                                outerRadius={100}
                                dataKey={valueKey}
                                nameKey={nameKey}
                                stroke="#0d1117"
                                strokeWidth={2}
                            >
                                {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: "#161b22", border: "1px solid #30363d", color: "#fff", borderRadius: "8px", boxShadow: "0 4px 12px rgba(0,0,0,0.4)", fontSize: 13 }}
                                formatter={(value: any, name: string) => [`${formatTooltipAmount(Number(value || 0))} · ${((Number(value || 0) / total) * 100).toFixed(1)}%`, name]}
                            />
                        </RechartsPieChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-gray-500 text-xs font-medium uppercase tracking-wider">Total</span>
                        <span className="text-[#daa520] font-bold text-lg mt-0.5">{formatAmount(total)}</span>
                    </div>
                </div>
                {/* Legend: color box + name + percentage — below donut, easy to scan */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 mt-4 w-full max-w-md px-2">
                    {chartData.map((entry, index) => (
                        <div
                            key={index}
                            className="flex items-center gap-3 py-1.5 rounded px-2 -mx-2 hover:bg-[#21262d] cursor-default transition-colors"
                            onMouseEnter={() => setActiveIndex(index)}
                            onMouseLeave={() => setActiveIndex(null)}
                        >
                            <div className="w-4 h-4 rounded flex-shrink-0 border border-[#30363d]" style={{ backgroundColor: entry.fill }} />
                            <span className="text-gray-200 text-sm truncate flex-1 min-w-0" title={String(entry[nameKey])}>
                                {String(entry[nameKey]).length > 32 ? `${String(entry[nameKey]).slice(0, 30)}…` : entry[nameKey]}
                            </span>
                            <span className="text-[#daa520] font-semibold text-sm flex-shrink-0">{entry._pct.toFixed(1)}%</span>
                        </div>
                    ))}
                </div>
            </div>
        </ChartWrapper>
    );
}

// 3. Scatter Bubble Chart (3D Data Points for RFM Analysis)
export function ScatterBubbleChart({ data, xKey, yKey, zKey, nameKey }: { data: any[]; xKey: string; yKey: string; zKey: string; nameKey: string }) {
    const formatAmt = (val: number) => formatTooltipAmount(val);
    const hasData = Array.isArray(data) && data.length > 0;
    if (!hasData) return <ChartEmpty message="No RFM data to display" />;

    return (
        <ChartWrapper className="min-h-[384px] w-full mt-4">
            <ResponsiveContainer width="100%" height={384}>
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                    <XAxis type="number" dataKey={xKey} name="Recency (Days)" stroke="#8b949e" tick={{ fill: "#8b949e" }} />
                    <YAxis type="number" dataKey={yKey} name="Frequency" stroke="#8b949e" tick={{ fill: "#8b949e" }} />
                    <ZAxis type="number" dataKey={zKey} range={[50, 800]} name="Monetary" />
                    <Tooltip
                        cursor={{ strokeDasharray: '3 3' }}
                        contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d', color: '#fff', borderRadius: '8px' }}
                        formatter={(value: any, name?: string) => name === 'Monetary' ? formatAmt(value) : value}
                    />
                    <Scatter name="Customers" data={data} fill="#daa520" fillOpacity={0.6}>
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Scatter>
                </ScatterChart>
            </ResponsiveContainer>
            <p className="text-center text-xs text-gray-500 mt-2">X: Recency (Days) | Y: Purchase Frequency | Bubble Size: Monetary Value</p>
        </ChartWrapper>
    );
}

// 4. Treemap — clear tiles + legend below so every name is readable
const TREEMAP_TILE_PADDING = 3;
const TREEMAP_STROKE = "#0d1117";

const CustomizedContent = (props: any) => {
    const { depth, x, y, width, height, index, value, payload, root } = props;
    const nodeVal = Number(value ?? payload?.value ?? payload?.AMOUNT ?? 0);
    const totalVal = Number(root?.value ?? 1);
    const pct = totalVal > 0 ? (nodeVal / totalVal) * 100 : 0;
    const fill = depth < 2 ? SEGMENT_COLORS[index % SEGMENT_COLORS.length] : "#21262d";
    const pad = TREEMAP_TILE_PADDING;
    const innerW = Math.max(0, width - pad * 2);
    const innerH = Math.max(0, height - pad * 2);
    const showPctOnly = innerW > 48 && innerH > 28;

    return (
        <g>
            <rect
                x={x + pad}
                y={y + pad}
                width={innerW}
                height={innerH}
                rx={4}
                ry={4}
                style={{ fill, stroke: TREEMAP_STROKE, strokeWidth: 2 }}
            />
            {showPctOnly && totalVal > 0 && (
                <text
                    x={x + width / 2}
                    y={y + height / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="#fff"
                    fontSize={14}
                    fontWeight={700}
                    style={{ textShadow: "0 1px 3px rgba(0,0,0,0.9)" }}
                >
                    {pct.toFixed(1)}%
                </text>
            )}
        </g>
    );
};

export function ModernTreemap({ data, nameKey, valueKey }: { data: any[]; nameKey: string; valueKey: string }) {
    if (!data || data.length === 0) return <ChartEmpty message="No data available" />;

    const total = data.reduce((s, d) => s + (Number(d[valueKey]) || 0), 0);

    return (
        <ChartWrapper className="min-h-[380px]">
            <div className="flex flex-col w-full">
                <div className="w-full" style={{ height: 280 }}>
                    <ResponsiveContainer width="100%" height={280}>
                        <Treemap
                            data={data}
                            dataKey={valueKey}
                            nameKey={nameKey}
                            stroke={TREEMAP_STROKE}
                            fill="#daa520"
                            content={<CustomizedContent />}
                        >
                            <Tooltip
                                contentStyle={{ backgroundColor: "#161b22", border: "1px solid #30363d", color: "#fff", borderRadius: "8px", fontSize: 13 }}
                                formatter={(value: any, name: string) => {
                                    const pct = total > 0 ? ((Number(value || 0) / total) * 100).toFixed(1) : "0";
                                    return [`${formatTooltipAmount(Number(value || 0))} · ${pct}%`, name];
                                }}
                            />
                        </Treemap>
                    </ResponsiveContainer>
                </div>
                {/* Legend: full names readable — color + name + % */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 mt-4 w-full max-w-2xl px-1">
                    {data.map((entry, index) => {
                        const val = Number(entry[valueKey]) || 0;
                        const pct = total > 0 ? (val / total) * 100 : 0;
                        const name = String(entry[nameKey] ?? "").trim();
                        return (
                            <div key={index} className="flex items-center gap-3 py-1.5 rounded px-2 -mx-2 hover:bg-[#21262d] transition-colors">
                                <div className="w-4 h-4 rounded flex-shrink-0 border border-[#30363d]" style={{ backgroundColor: SEGMENT_COLORS[index % SEGMENT_COLORS.length] }} />
                                <span className="text-gray-200 text-sm flex-1 min-w-0 break-words" title={name}>
                                    {name}
                                </span>
                                <span className="text-[#daa520] font-semibold text-sm flex-shrink-0">{pct.toFixed(1)}%</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </ChartWrapper>
    );
}

// Horizontal bar chart — full names on the left, no truncation (alternative to donut/treemap)
export function CategoryHorizontalBarChart({ data, nameKey, valueKey, title }: { data: any[]; nameKey: string; valueKey: string; title?: string }) {
    const hasData = Array.isArray(data) && data.length > 0;
    if (!hasData) return <ChartEmpty message="No data to display" />;

    const total = data.reduce((s, d) => s + (Number(d[valueKey]) || 0), 0);
    const maxVal = Math.max(...data.map((d) => Number(d[valueKey]) || 0), 1);

    return (
        <ChartWrapper className="min-h-[320px]">
            {title && <p className="text-sm text-gray-400 mb-2">{title}</p>}
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
                {data.map((entry, index) => {
                    const val = Number(entry[valueKey]) || 0;
                    const pct = total > 0 ? (val / total) * 100 : 0;
                    const name = String(entry[nameKey] ?? "").trim();
                    const barW = maxVal > 0 ? (val / maxVal) * 100 : 0;
                    return (
                        <div key={index} className="flex items-center gap-3 group">
                            <span className="text-gray-200 text-sm min-w-0 flex-[1_1_35%] max-w-[50%] break-words" title={name}>
                                {name}
                            </span>
                            <div className="flex-1 min-w-0 h-7 bg-[#21262d] rounded overflow-hidden">
                                <div
                                    className="h-full rounded flex items-center justify-end pr-2 transition-all"
                                    style={{
                                        width: `${barW}%`,
                                        minWidth: val > 0 ? "2rem" : 0,
                                        backgroundColor: SEGMENT_COLORS[index % SEGMENT_COLORS.length],
                                    }}
                                >
                                    {barW > 15 && (
                                        <span className="text-xs font-semibold text-white drop-shadow-sm">
                                            {formatAmount(val)}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <span className="text-[#daa520] font-semibold text-sm w-12 text-right flex-shrink-0">
                                {pct.toFixed(1)}%
                            </span>
                        </div>
                    );
                })}
            </div>
        </ChartWrapper>
    );
}

export function BarChart({ data, xKey, yKey }: { data: any[]; xKey: string; yKey: string }) {
    const hasData = Array.isArray(data) && data.length > 0;
    if (!hasData) return <ChartEmpty message="No data to display" />;

    return (
        <ChartWrapper>
            <ResponsiveContainer width="100%" height={320}>
                <RechartsBarChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#30363d" vertical={false} />
                    <XAxis
                        dataKey={xKey}
                        stroke="#8b949e"
                        tick={{ fill: "#8b949e" }}
                        tickLine={false}
                        axisLine={false}
                    />
                    <YAxis
                        stroke="#8b949e"
                        tick={{ fill: "#8b949e" }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(val) => formatAxisTick(val)}
                    />
                    <Tooltip
                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                        contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d', color: '#fff' }}
                        formatter={(value: any) => formatTooltipAmount(Number(value || 0))}
                    />
                    <Bar dataKey={yKey} fill="#daa520" radius={[4, 4, 0, 0]} barSize={40} />
                </RechartsBarChart>
            </ResponsiveContainer>
        </ChartWrapper>
    );
}
