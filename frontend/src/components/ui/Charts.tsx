"use client";

import React from "react";
import {
    BarChart as RechartsBarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart as RechartsPieChart,
    Pie,
    Cell,
} from "recharts";

const COLORS = ["#daa520", "#a87f17", "#735c1d", "#4b4122", "#2d2a1d"];

export function BarChart({ data, xKey, yKey }: { data: any[]; xKey: string; yKey: string }) {
    return (
        <div className="h-80 w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
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
                        tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`}
                    />
                    <Tooltip
                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                        contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d', color: '#fff' }}
                        formatter={(value: number) => [`₹${(value / 100000).toFixed(2)} Lakhs`, "Revenue"]}
                    />
                    <Bar dataKey={yKey} fill="#daa520" radius={[4, 4, 0, 0]} barSize={40} />
                </RechartsBarChart>
            </ResponsiveContainer>
        </div>
    );
}

export function PieChart({ data, nameKey, valueKey }: { data: any[]; nameKey: string; valueKey: string }) {
    return (
        <div className="h-80 w-full flex justify-center items-center mt-4">
            <ResponsiveContainer width="100%" height="100%">
                <RechartsPieChart>
                    <Pie
                        data={data}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={5}
                        dataKey={valueKey}
                        nameKey={nameKey}
                        label={({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }) => {
                            const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
                            return `${(percent * 100).toFixed(0)}%`;
                        }}
                    >
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip
                        contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d', color: '#fff' }}
                        formatter={(value: number) => [`₹${(value / 100000).toFixed(2)} Lakhs`, "Revenue"]}
                    />
                </RechartsPieChart>
            </ResponsiveContainer>
        </div>
    );
}
