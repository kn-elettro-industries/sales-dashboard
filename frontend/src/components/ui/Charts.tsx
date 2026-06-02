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
    Bar,
    LabelList,
    ComposedChart,
    Line,
    ReferenceLine,
    ReferenceArea,
} from "recharts";

// High-contrast segment colors — each slice clearly distinct (donut & treemap)
const SEGMENT_COLORS = [
    "#f4c430", "#0ea5e9", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899",
    "#14b8a6", "#e11d48", "#6366f1", "#84cc16", "#f97316", "#06b6d4"
];
// Legacy alias for other charts
const COLORS = SEGMENT_COLORS;

// RFM segment → colour (exported so customers page can reuse)
export const RFM_SEGMENT_COLORS: Record<string, string> = {
    "Champions": "#22c55e",
    "Loyal":     "#3b82f6",
    "Potential": "#f59e0b",
    "At Risk":   "#f97316",
    "Lost":      "#ef4444",
};

/** Recharts defaults tooltip *values* to black; itemStyle/labelStyle + globals.css fix contrast on dark UI */
const CHART_TOOLTIP_BASE = {
    contentStyle: {
        backgroundColor: "var(--chart-panel-bg)",
        border: "1px solid var(--chart-panel-border)",
        borderRadius: "8px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.35)",
    },
    labelStyle: {
        color: "var(--app-gold)",
        fontWeight: 600 as const,
    },
    itemStyle: {
        color: "var(--chart-tooltip-row)",
    },
    wrapperStyle: { outline: "none" as const, zIndex: 50 },
};

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
        <div className="flex flex-col items-center justify-center h-[320px] w-full text-app-fg-muted gap-2">
            <svg className="w-8 h-8 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
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
                            <stop offset="5%" stopColor="var(--app-gold)" stopOpacity={0.9} />
                            <stop offset="95%" stopColor="var(--app-gold)" stopOpacity={0.08} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" vertical={false} opacity={0.8} />
                    <XAxis dataKey={xKey} stroke="var(--chart-axis)" tick={{ fill: "var(--chart-axis)", fontSize: 12 }} tickLine={false} axisLine={false} />
                    <YAxis
                        stroke="var(--chart-axis)"
                        tick={{ fill: "var(--chart-axis)", fontSize: 12 }}
                        tickLine={false}
                        axisLine={false}
                        width={48}
                        tickFormatter={(val) => formatCurrency ? formatAxisTick(val) : String(val)}
                    />
                    <Tooltip
                        {...CHART_TOOLTIP_BASE}
                        contentStyle={{ ...CHART_TOOLTIP_BASE.contentStyle, fontSize: 13 }}
                        formatter={(value: any) => [formatCurrency ? `₹ ${Number(value || 0).toLocaleString("en-IN")}` : value, "Revenue"]}
                    />
                    <Area type="monotone" dataKey={yKey} stroke="var(--app-gold)" strokeWidth={2.5} fillOpacity={1} fill="url(#colorYKey)" dot={false} activeDot={{ r: 5, fill: "var(--app-gold)", stroke: "var(--chart-panel-bg)", strokeWidth: 2 }} />
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
                                stroke="var(--chart-invert)"
                                strokeWidth={2}
                            >
                                {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill} />
                                ))}
                            </Pie>
                            <Tooltip
                                {...CHART_TOOLTIP_BASE}
                                contentStyle={{ ...CHART_TOOLTIP_BASE.contentStyle, fontSize: 13 }}
                                formatter={(value: any, name: string | undefined) => [`${formatTooltipAmount(Number(value || 0))} · ${((Number(value || 0) / total) * 100).toFixed(1)}%`, name ?? ""]}
                            />
                        </RechartsPieChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-app-fg-muted text-xs font-medium uppercase tracking-wider">Total</span>
                        <span className="text-app-gold font-bold text-lg mt-0.5">{formatAmount(total)}</span>
                    </div>
                </div>
                {/* Legend: color box + name + percentage — below donut, easy to scan */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 mt-4 w-full max-w-md px-2">
                    {chartData.map((entry, index) => (
                        <div
                            key={index}
                            className="flex items-center gap-3 py-1.5 rounded px-2 -mx-2 hover:bg-app-hover cursor-default transition-colors"
                            onMouseEnter={() => setActiveIndex(index)}
                            onMouseLeave={() => setActiveIndex(null)}
                        >
                            <div className="w-4 h-4 rounded flex-shrink-0 border border-app-border" style={{ backgroundColor: entry.fill }} />
                            <span className="text-app-fg text-sm truncate flex-1 min-w-0" title={String(entry[nameKey])}>
                                {String(entry[nameKey]).length > 32 ? `${String(entry[nameKey]).slice(0, 30)}…` : entry[nameKey]}
                            </span>
                            <span className="text-app-gold font-semibold text-sm flex-shrink-0">{entry._pct.toFixed(1)}%</span>
                        </div>
                    ))}
                </div>
            </div>
        </ChartWrapper>
    );
}

// 3. Scatter Bubble Chart (3D Data Points for RFM Analysis)
export function ScatterBubbleChart({ data, xKey, yKey, zKey, nameKey, segmentKey }: {
    data: any[]; xKey: string; yKey: string; zKey: string; nameKey: string; segmentKey?: string;
}) {
    const formatAmt = (val: number) => formatTooltipAmount(val);
    const hasData = Array.isArray(data) && data.length > 0;
    if (!hasData) return <ChartEmpty message="No RFM data to display" />;

    // Compute medians for quadrant reference lines
    const xVals = data.map(d => Number(d[xKey]) || 0).sort((a, b) => a - b);
    const yVals = data.map(d => Number(d[yKey]) || 0).sort((a, b) => a - b);
    const xMid = xVals[Math.floor(xVals.length / 2)] ?? 0;
    const yMid = yVals[Math.floor(yVals.length / 2)] ?? 0;
    const xMax = xVals[xVals.length - 1] ?? xMid * 2;
    const yMax = yVals[yVals.length - 1] ?? yMid * 2;

    const segmentDot = (seg: string) => RFM_SEGMENT_COLORS[seg] ?? "#f4c430";

    return (
        <ChartWrapper className="min-h-[420px] w-full mt-4">
            <ResponsiveContainer width="100%" height={400}>
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    {/* Quadrant background shading */}
                    <ReferenceArea x1={0} x2={xMid} y1={yMid} y2={yMax * 1.1} fill="#22c55e" fillOpacity={0.06} />
                    <ReferenceArea x1={xMid} x2={xMax * 1.1} y1={yMid} y2={yMax * 1.1} fill="#3b82f6" fillOpacity={0.06} />
                    <ReferenceArea x1={0} x2={xMid} y1={0} y2={yMid} fill="#f59e0b" fillOpacity={0.06} />
                    <ReferenceArea x1={xMid} x2={xMax * 1.1} y1={0} y2={yMid} fill="#ef4444" fillOpacity={0.06} />

                    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                    <XAxis type="number" dataKey={xKey} name="Recency (Days)" stroke="var(--chart-axis)" tick={{ fill: "var(--chart-axis)", fontSize: 11 }} label={{ value: "Recency (days since last order) →", position: "insideBottom", offset: -10, fill: "var(--chart-axis)", fontSize: 11 }} />
                    <YAxis type="number" dataKey={yKey} name="Frequency" stroke="var(--chart-axis)" tick={{ fill: "var(--chart-axis)", fontSize: 11 }} label={{ value: "Frequency (orders) →", angle: -90, position: "insideLeft", fill: "var(--chart-axis)", fontSize: 11 }} />
                    <ZAxis type="number" dataKey={zKey} range={[50, 800]} name="Monetary" />
                    <Tooltip
                        cursor={{ strokeDasharray: "3 3" }}
                        wrapperStyle={CHART_TOOLTIP_BASE.wrapperStyle}
                        content={({ active, payload }) => {
                            if (!active || !payload?.length) return null;
                            const raw = payload[0] as { payload?: Record<string, unknown> } & Record<string, unknown>;
                            const row = (raw?.payload ?? raw) as Record<string, unknown> | undefined;
                            if (!row || typeof row !== "object") return null;
                            const customer = String(row[nameKey] ?? "").trim() || "—";
                            const seg = segmentKey ? String(row[segmentKey] ?? "") : "";
                            const rec = row[xKey]; const freq = row[yKey]; const mon = row[zKey];
                            const rowStyle = { color: "var(--chart-tooltip-row)" as const, fontSize: 12, margin: "2px 0 0 0" };
                            const labelStyle = { color: "var(--chart-axis)" as const, fontSize: 11, margin: "6px 0 0 0" };
                            return (
                                <div style={{ ...CHART_TOOLTIP_BASE.contentStyle, padding: "10px 12px", fontSize: 13 }}>
                                    <div style={{ color: "var(--app-gold)", fontWeight: 700, fontSize: 13, marginBottom: 4, wordBreak: "break-word" }}>{customer}</div>
                                    {seg && <div style={{ color: segmentDot(seg), fontWeight: 600, fontSize: 11, marginBottom: 8 }}>● {seg}</div>}
                                    <div style={labelStyle}>Recency (days)</div>
                                    <div style={rowStyle}>{rec != null ? Number(rec).toLocaleString("en-IN") : "—"}</div>
                                    <div style={labelStyle}>Frequency</div>
                                    <div style={rowStyle}>{freq != null ? Number(freq).toLocaleString("en-IN") : "—"}</div>
                                    <div style={labelStyle}>Monetary (revenue)</div>
                                    <div style={{ ...rowStyle, color: "var(--app-gold)", fontWeight: 600 }}>{mon != null ? formatAmt(Number(mon)) : "—"}</div>
                                </div>
                            );
                        }}
                    />
                    <Scatter name="Customers" data={data} fillOpacity={0.75}>
                        {data.map((entry, index) => {
                            const seg = segmentKey ? String(entry[segmentKey] ?? "") : "";
                            return <Cell key={`cell-${index}`} fill={seg ? (RFM_SEGMENT_COLORS[seg] ?? COLORS[index % COLORS.length]) : COLORS[index % COLORS.length]} />;
                        })}
                    </Scatter>
                </ScatterChart>
            </ResponsiveContainer>
            {/* Segment legend */}
            <div className="flex flex-wrap justify-center gap-4 mt-2">
                {Object.entries(RFM_SEGMENT_COLORS).map(([seg, color]) => (
                    <span key={seg} className="flex items-center gap-1.5 text-xs text-app-fg-muted">
                        <span className="w-2.5 h-2.5 rounded-full inline-block flex-shrink-0" style={{ backgroundColor: color }} />
                        {seg}
                    </span>
                ))}
                <span className="text-xs text-app-fg-muted ml-2">· Bubble size = Revenue</span>
            </div>
        </ChartWrapper>
    );
}

// 4. Treemap — clear tiles + legend below so every name is readable
const TREEMAP_TILE_PADDING = 3;
const TREEMAP_STROKE = "var(--chart-invert)";

const CustomizedContent = (props: any) => {
    const { depth, x, y, width, height, index, value, payload, root } = props;
    const nodeVal = Number(value ?? payload?.value ?? payload?.AMOUNT ?? 0);
    const totalVal = Number(root?.value ?? 1);
    const pct = totalVal > 0 ? (nodeVal / totalVal) * 100 : 0;
    const fill = depth < 2 ? SEGMENT_COLORS[index % SEGMENT_COLORS.length] : "var(--chart-treemap-deep)";
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

export function ModernTreemap({ data, nameKey, valueKey, onCellClick }: {
    data: any[]; nameKey: string; valueKey: string; onCellClick?: (name: string) => void;
}) {
    if (!data || data.length === 0) return <ChartEmpty message="No data available" />;

    const total = data.reduce((s, d) => s + (Number(d[valueKey]) || 0), 0);

    return (
        <ChartWrapper className="min-h-[380px]">
            <div className="flex flex-col w-full">
                {onCellClick && (
                    <p className="text-xs text-app-fg-muted mb-2">Click a tile to see individual items</p>
                )}
                <div className="w-full" style={{ height: 280 }}>
                    <ResponsiveContainer width="100%" height={280}>
                        <Treemap
                            data={data}
                            dataKey={valueKey}
                            nameKey={nameKey}
                            stroke={TREEMAP_STROKE}
                            fill="var(--app-gold)"
                            content={<CustomizedContent />}
                            onClick={(node: any) => {
                                const name = node?.[nameKey] ?? node?.name ?? node?.root?.[nameKey];
                                if (name && onCellClick) onCellClick(String(name));
                            }}
                            style={onCellClick ? { cursor: "pointer" } : undefined}
                        >
                            <Tooltip
                                {...CHART_TOOLTIP_BASE}
                                contentStyle={{ ...CHART_TOOLTIP_BASE.contentStyle, fontSize: 13 }}
                                formatter={(value: any, name: string | undefined) => {
                                    const pct = total > 0 ? ((Number(value || 0) / total) * 100).toFixed(1) : "0";
                                    return [`${formatTooltipAmount(Number(value || 0))} · ${pct}%`, name ?? ""];
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
                            <div
                                key={index}
                                className={`flex items-center gap-3 py-1.5 rounded px-2 -mx-2 transition-colors ${onCellClick ? "cursor-pointer hover:bg-app-hover" : "hover:bg-app-hover"}`}
                                onClick={() => onCellClick && onCellClick(name)}
                            >
                                <div className="w-4 h-4 rounded flex-shrink-0 border border-app-border" style={{ backgroundColor: SEGMENT_COLORS[index % SEGMENT_COLORS.length] }} />
                                <span className="text-app-fg text-sm flex-1 min-w-0 break-words" title={name}>
                                    {name}
                                </span>
                                <span className="text-app-gold font-semibold text-sm flex-shrink-0">{pct.toFixed(1)}%</span>
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
            {title && <p className="text-sm text-app-fg-muted mb-2">{title}</p>}
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
                {data.map((entry, index) => {
                    const val = Number(entry[valueKey]) || 0;
                    const pct = total > 0 ? (val / total) * 100 : 0;
                    const name = String(entry[nameKey] ?? "").trim();
                    const barW = maxVal > 0 ? (val / maxVal) * 100 : 0;
                    return (
                        <div key={index} className="flex items-center gap-3 group">
                            <span className="text-app-fg text-sm min-w-0 flex-[1_1_35%] max-w-[50%] break-words" title={name}>
                                {name}
                            </span>
                            <div className="flex-1 min-w-0 h-7 bg-app-hover rounded overflow-hidden relative">
                                <div
                                    className="h-full rounded transition-all"
                                    style={{
                                        width: `${barW}%`,
                                        minWidth: val > 0 ? "2rem" : 0,
                                        backgroundColor: SEGMENT_COLORS[index % SEGMENT_COLORS.length],
                                    }}
                                />
                            </div>
                            <span className="text-xs font-semibold text-app-fg w-20 text-right flex-shrink-0">
                                {formatAmount(val)}
                            </span>
                            <span className="text-app-gold text-xs w-10 text-right flex-shrink-0">
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
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" vertical={false} />
                    <XAxis
                        dataKey={xKey}
                        stroke="var(--chart-axis)"
                        tick={{ fill: "var(--chart-axis)" }}
                        tickLine={false}
                        axisLine={false}
                    />
                    <YAxis
                        stroke="var(--chart-axis)"
                        tick={{ fill: "var(--chart-axis)" }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(val) => formatAxisTick(val)}
                    />
                    <Tooltip
                        {...CHART_TOOLTIP_BASE}
                        cursor={{ fill: "var(--chart-bar-cursor)" }}
                        contentStyle={{ ...CHART_TOOLTIP_BASE.contentStyle, fontSize: 13 }}
                        formatter={(value: any) => formatTooltipAmount(Number(value || 0))}
                    />
                    <Bar dataKey={yKey} fill="var(--app-gold)" radius={[4, 4, 0, 0]} barSize={40}>
                        <LabelList dataKey={yKey} position="top" style={{ fill: "var(--chart-axis)", fontSize: 11 }} formatter={(v: any) => formatAxisTick(Number(v))} />
                    </Bar>
                </RechartsBarChart>
            </ResponsiveContainer>
        </ChartWrapper>
    );
}

// Pareto curve — bars (individual share %) + line (cumulative %) + 80/95 reference lines
export function ParetoChart({ data, nameKey, shareKey, cumulativeKey }: {
    data: any[]; nameKey: string; shareKey: string; cumulativeKey: string;
}) {
    if (!data || data.length === 0) return <ChartEmpty message="No Pareto data" />;

    const classColor = (d: any) =>
        d.Class === "A" ? "#22c55e" : d.Class === "B" ? "#f59e0b" : "#ef4444";

    return (
        <ChartWrapper className="min-h-[300px] w-full">
            <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={data} margin={{ top: 16, right: 40, left: 0, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" vertical={false} />
                    <XAxis dataKey={nameKey} tick={false} axisLine={false} tickLine={false} />
                    <YAxis
                        yAxisId="left"
                        stroke="var(--chart-axis)"
                        tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `${v}%`}
                        domain={[0, "auto"]}
                    />
                    <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="var(--chart-axis)"
                        tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `${v}%`}
                        domain={[0, 100]}
                    />
                    <Tooltip
                        {...CHART_TOOLTIP_BASE}
                        contentStyle={{ ...CHART_TOOLTIP_BASE.contentStyle, fontSize: 12 }}
                        formatter={(value: any, name: string | undefined) => [`${Number(value).toFixed(1)}%`, name ?? ""]}
                        labelFormatter={(label) => String(label).slice(0, 40)}
                    />
                    {/* 80% and 95% threshold lines */}
                    <ReferenceLine yAxisId="right" y={80} stroke="#22c55e" strokeDasharray="6 3" strokeWidth={1.5}
                        label={{ value: "80% (A)", position: "right", fill: "#22c55e", fontSize: 10 }} />
                    <ReferenceLine yAxisId="right" y={95} stroke="#f59e0b" strokeDasharray="6 3" strokeWidth={1.5}
                        label={{ value: "95% (B)", position: "right", fill: "#f59e0b", fontSize: 10 }} />
                    <Bar yAxisId="left" dataKey={shareKey} name="Share %" radius={[2, 2, 0, 0]}>
                        {data.map((entry, i) => <Cell key={i} fill={classColor(entry)} fillOpacity={0.8} />)}
                    </Bar>
                    <Line yAxisId="right" type="monotone" dataKey={cumulativeKey} name="Cumulative %" stroke="var(--app-gold)" strokeWidth={2} dot={false} />
                </ComposedChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-6 mt-1 text-xs text-app-fg-muted">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm inline-block bg-green-500" />A — top 80%</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm inline-block bg-yellow-500" />B — next 15%</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm inline-block bg-red-500" />C — bottom 5%</span>
                <span className="flex items-center gap-1"><span className="w-3 h-0.5 inline-block bg-app-gold" />Cumulative %</span>
            </div>
        </ChartWrapper>
    );
}
