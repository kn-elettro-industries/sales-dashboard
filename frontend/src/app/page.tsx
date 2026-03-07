"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useFilter } from "@/components/FilterContext";
import { DataTable } from "@/components/ui/DataTable";
import { format } from "date-fns";
import { fetchDashboardSummary, fetchAnomalies } from "@/lib/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { GradientAreaChart, InteractiveDonutChart, CategoryHorizontalBarChart } from "@/components/ui/Charts";
import { IndianRupee, ShoppingCart, Users, TrendingUp, AlertTriangle } from "lucide-react";
import { formatAmount } from "@/lib/format";

export default function DashboardPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths } = useFilter();
    const [data, setData] = useState<any>({ summary: null, trend: [], materials: [], customers: [] });
    const [anomalies, setAnomalies] = useState<{ entity: string; change_pct: number; current_revenue: number }[]>([]);
    const [loading, setLoading] = useState(true);
    const [showTargets, setShowTargets] = useState(false);
    const [materialChartView, setMaterialChartView] = useState<"donut" | "bar">("donut");
    const [goalRevenue, setGoalRevenue] = useState<number | null>(null);
    const [goalOrders, setGoalOrders] = useState<number | null>(null);

    useEffect(() => {
        const r = localStorage.getItem("elettro_goal_revenue");
        const o = localStorage.getItem("elettro_goal_orders");
        if (r) setGoalRevenue(Number(r));
        if (o) setGoalOrders(Number(o));
    }, []);

    useEffect(() => {
        async function loadData() {
            setLoading(true);

            const p = {
                tenant,
                startDate: dateRange?.from ? format(dateRange.from, 'yyyy-MM-dd') : undefined,
                endDate: dateRange?.to ? format(dateRange.to, 'yyyy-MM-dd') : undefined,
                states: selectedStates.length > 0 ? selectedStates.join(',') : undefined,
                cities: selectedCities.length > 0 ? selectedCities.join(',') : undefined,
                customers: selectedCustomers.length > 0 ? selectedCustomers.join(',') : undefined,
                materialGroups: selectedMaterialGroups.length > 0 ? selectedMaterialGroups.join(',') : undefined,
                fiscalYears: selectedFiscalYears.length > 0 ? selectedFiscalYears.join(',') : undefined,
                months: selectedMonths.length > 0 ? selectedMonths.join(',') : undefined,
                goalRevenue: goalRevenue ?? undefined,
                goalOrders: goalOrders ?? undefined,
            };

            try {
                const res = await fetchDashboardSummary(p);
                if (!res) {
                    setData({ summary: null, trend: [], materials: [], customers: [] });
                } else {
                    setData({
                        summary: res.summary ?? null,
                        trend: res.trend ?? [],
                        materials: res.material_groups ?? [],
                        customers: res.top_customers ?? [],
                    });
                }
                const anom = await fetchAnomalies({
                    tenant,
                    startDate: p.startDate,
                    endDate: p.endDate,
                    states: selectedStates.length > 0 ? selectedStates.join(",") : undefined,
                    customers: selectedCustomers.length > 0 ? selectedCustomers.join(",") : undefined,
                    materialGroups: selectedMaterialGroups.length > 0 ? selectedMaterialGroups.join(",") : undefined,
                    fiscalYears: selectedFiscalYears.length > 0 ? selectedFiscalYears.join(",") : undefined,
                    months: selectedMonths.length > 0 ? selectedMonths.join(",") : undefined,
                    dropThresholdPct: 20,
                });
                setAnomalies(anom?.anomalies ?? []);
            } catch (e) {
                console.error("Failed to fetch dashboard data", e);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, goalRevenue, goalOrders]);

    const fmt = formatAmount;
    const sum = data.summary || { revenue: 0, orders: 0, customers: 0, average_order_value: 0 };
    const comp = data.comparison || null;
    const goals = data.goals || null;

    const validTrend = Array.isArray(data.trend) ? data.trend : [];
    const validMat = Array.isArray(data.materials) ? data.materials : [];
    const validCust = Array.isArray(data.customers) ? data.customers : [];

    const tableMat = React.useMemo(() => {
        return validMat.map((m: any) => ({
            name: Object.keys(m).find(k => k !== 'AMOUNT') ? m[Object.keys(m).find(k => k !== 'AMOUNT')!] : 'Unknown',
            AMOUNT: m.AMOUNT
        }));
    }, [validMat]);

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            {showTargets && (
                <div className="flex flex-wrap items-center gap-4 p-4 bg-[#161b22] border border-[#30363d] rounded-xl">
                    <span className="text-sm text-gray-400">Targets (saved in browser):</span>
                    <label className="flex items-center gap-2 text-sm">
                        Revenue (₹): <input type="number" min="0" step="10000" value={goalRevenue ?? ""} onChange={(e) => { const v = e.target.value ? Number(e.target.value) : null; setGoalRevenue(v); if (v != null) localStorage.setItem("elettro_goal_revenue", String(v)); else localStorage.removeItem("elettro_goal_revenue"); }} className="w-32 bg-[#0d1117] border border-[#30363d] rounded px-2 py-1 text-white" placeholder="Optional" />
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                        Orders: <input type="number" min="0" value={goalOrders ?? ""} onChange={(e) => { const v = e.target.value ? Number(e.target.value) : null; setGoalOrders(v); if (v != null) localStorage.setItem("elettro_goal_orders", String(v)); else localStorage.removeItem("elettro_goal_orders"); }} className="w-28 bg-[#0d1117] border border-[#30363d] rounded px-2 py-1 text-white" placeholder="Optional" />
                    </label>
                    <button type="button" onClick={() => setShowTargets(false)} className="text-sm text-gray-500 hover:text-white">Hide</button>
                </div>
            )}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-white">Executive Summary</h2>
                <button type="button" onClick={() => setShowTargets((s) => !s)} className="text-sm text-[#daa520] hover:underline">{showTargets ? "Hide targets" : "Set revenue/order targets"}</button>
            </div>
            {!loading && (!data.summary || (sum.revenue === 0 && sum.orders === 0)) && validTrend.length === 0 && (
                <div className="p-4 bg-amber-900/20 border border-amber-700 rounded-xl">
                    <h3 className="text-sm font-semibold text-amber-400 flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4" /> No data yet
                    </h3>
                    <ul className="text-sm text-gray-300 space-y-1 list-disc list-inside">
                        <li>Set <code className="bg-[#0d1117] px-1 rounded">NEXT_PUBLIC_API_URL</code> to your Render API (e.g. <code className="bg-[#0d1117] px-1 rounded">https://xxx.onrender.com/api</code>) in Vercel → Settings → Environment Variables, then <strong>redeploy</strong>.</li>
                        <li>If the API is correct, upload data from the <strong><Link href="/data" className="text-[#daa520] hover:underline">Data</Link></strong> page (Excel/CSV with DATE, INVOICE_NO, CUSTOMER_NAME, AMOUNT, etc.).</li>
                    </ul>
                </div>
            )}
            {anomalies.length > 0 && (
                <div className="p-4 bg-red-900/20 border border-red-800 rounded-xl">
                    <h3 className="text-sm font-semibold text-red-400 flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4" /> Revenue drop vs previous period (&gt;20%)
                    </h3>
                    <ul className="text-sm text-gray-300 space-y-1">
                        {anomalies.slice(0, 5).map((a) => (
                            <li key={a.entity}>
                                <span className="font-medium text-white">{a.entity}</span>
                                <span className="text-red-400 ml-2">{a.change_pct}%</span>
                            </li>
                        ))}
                        {anomalies.length > 5 && <li className="text-gray-500">+{anomalies.length - 5} more</li>}
                    </ul>
                </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <KpiCard
                    title="Total Revenue"
                    value={loading || !data.summary ? "—" : fmt(sum.revenue)}
                    icon={IndianRupee}
                    trend={comp ? `${comp.revenue_pct >= 0 ? "+" : ""}${comp.revenue_pct}%` : undefined}
                    trendUp={comp ? comp.revenue_pct >= 0 : undefined}
                    goalPct={goals?.revenue_achievement_pct}
                />
                <KpiCard
                    title="Total Orders"
                    value={loading || !data.summary ? "—" : sum.orders.toLocaleString()}
                    icon={ShoppingCart}
                    trend={comp ? `${comp.orders_pct >= 0 ? "+" : ""}${comp.orders_pct}%` : undefined}
                    trendUp={comp ? comp.orders_pct >= 0 : undefined}
                    goalPct={goals?.orders_achievement_pct}
                />
                <KpiCard
                    title="Active Customers"
                    value={loading || !data.summary ? "—" : sum.customers.toLocaleString()}
                    icon={Users}
                    trend={comp ? `${comp.customers_pct >= 0 ? "+" : ""}${comp.customers_pct}%` : undefined}
                    trendUp={comp ? comp.customers_pct >= 0 : undefined}
                />
                <KpiCard
                    title="Avg Order Value"
                    value={loading || !data.summary ? "—" : fmt(sum.average_order_value)}
                    icon={TrendingUp}
                    trend={comp ? `${comp.average_order_value_pct >= 0 ? "+" : ""}${comp.average_order_value_pct}%` : undefined}
                    trendUp={comp ? comp.average_order_value_pct >= 0 : undefined}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 bg-[#161b22] border border-[#30363d] rounded-xl p-6 min-h-[420px] flex flex-col">
                    <div className="border-l-4 border-[#daa520] pl-3 mb-4">
                        <h3 className="text-lg font-semibold text-white">Monthly Sales Trend</h3>
                        <p className="text-sm text-gray-400 mt-0.5">Revenue over the selected period</p>
                    </div>
                    {loading ? (
                        <div className="flex-1 min-h-[320px] rounded-lg bg-[#0d1117]/50 animate-pulse flex items-center justify-center border border-[#30363d]/50">
                            <span className="text-gray-500 text-sm">Loading chart...</span>
                        </div>
                    ) : (
                        <div className="flex-1 min-h-[320px]">
                            <GradientAreaChart data={validTrend} xKey="DATE" yKey="AMOUNT" formatCurrency={true} />
                        </div>
                    )}
                </div>

                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 min-h-[420px] flex flex-col">
                    <div className="border-l-4 border-[#daa520] pl-3 mb-4 flex items-center justify-between flex-wrap gap-2">
                        <div>
                            <h3 className="text-lg font-semibold text-white">Top Material Groups</h3>
                            <p className="text-sm text-gray-400 mt-0.5">By revenue share</p>
                        </div>
                        <div className="flex rounded-lg border border-[#30363d] p-0.5 bg-[#0d1117]">
                            <button type="button" onClick={() => setMaterialChartView("donut")} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${materialChartView === "donut" ? "bg-[#daa520] text-[#0d1117] font-medium" : "text-gray-400 hover:text-white"}`}>Donut</button>
                            <button type="button" onClick={() => setMaterialChartView("bar")} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${materialChartView === "bar" ? "bg-[#daa520] text-[#0d1117] font-medium" : "text-gray-400 hover:text-white"}`}>Bar</button>
                        </div>
                    </div>
                    {loading ? (
                        <div className="flex-1 min-h-[320px] rounded-lg bg-[#0d1117]/50 animate-pulse flex items-center justify-center border border-[#30363d]/50">
                            <span className="text-gray-500 text-sm">Loading chart...</span>
                        </div>
                    ) : (
                        <div className="flex-1 min-h-[320px]">
                            {materialChartView === "bar" ? (
                                <CategoryHorizontalBarChart data={validMat} nameKey={validMat.length > 0 ? Object.keys(validMat[0]).find(k => k !== "AMOUNT") || "name" : "name"} valueKey="AMOUNT" />
                            ) : (
                                <InteractiveDonutChart data={validMat} nameKey={validMat.length > 0 ? Object.keys(validMat[0]).find(k => k !== "AMOUNT") || "name" : "name"} valueKey="AMOUNT" />
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
                {/* Top Customers Table */}
                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 flex flex-col">
                    <h3 className="text-lg font-semibold text-white mb-4 border-b border-[#30363d] pb-4">Top Customers</h3>
                    <div className="flex-1 min-h-[400px]">
                        <DataTable
                            data={validCust}
                            searchable={true}
                            searchPlaceholder="Search customers..."
                            searchKeys={['CUSTOMER_NAME']}
                            pageSizeOptions={[5, 10, 20]}
                            defaultPageSize={10}
                            columns={[
                                { header: 'Customer', accessorKey: 'CUSTOMER_NAME', sortable: true },
                                {
                                    header: 'Revenue',
                                    accessorKey: 'AMOUNT',
                                    sortable: true,
                                    align: 'right',
                                    cell: (item: any) => <span className="text-white font-bold">{fmt(item.AMOUNT)}</span>
                                }
                            ]}
                        />
                    </div>
                </div>

                {/* Top Material Groups Table */}
                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 flex flex-col">
                    <h3 className="text-lg font-semibold text-white mb-4 border-b border-[#30363d] pb-4">Top Performers (Material Groups)</h3>
                    <div className="flex-1 min-h-[400px]">
                        <DataTable
                            data={tableMat}
                            searchable={true}
                            searchPlaceholder="Search materials..."
                            searchKeys={['name']}
                            pageSizeOptions={[5, 10, 20]}
                            defaultPageSize={10}
                            columns={[
                                { header: 'Material Group', accessorKey: 'name', sortable: true },
                                {
                                    header: 'Revenue',
                                    accessorKey: 'AMOUNT',
                                    sortable: true,
                                    align: 'right',
                                    cell: (item: any) => <span className="text-white font-bold">{fmt(item.AMOUNT)}</span>
                                }
                            ]}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
