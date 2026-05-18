"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useFilter } from "@/components/FilterContext";
import { DataTable } from "@/components/ui/DataTable";
import { format } from "date-fns";
import { fetchDashboardSummary, fetchAnomalies, fetchKpiSummary, fetchSalesTrend, fetchMaterialGroups, fetchTopCustomers, saveSalesTargets } from "@/lib/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { GradientAreaChart, InteractiveDonutChart, CategoryHorizontalBarChart } from "@/components/ui/Charts";
import { IndianRupee, ShoppingCart, Users, TrendingUp, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { formatAmount } from "@/lib/format";

/** Columns from API that are not the material group name */
const MATERIAL_META = new Set(["AMOUNT", "SHARE_PCT", "TARGET_REVENUE", "VS_TARGET_PCT"]);

export default function DashboardPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems } = useFilter();
    const [data, setData] = useState<any>({ summary: null, trend: [], materials: [], customers: [], comparison: null, goals: null, sales_targets: null, message: null });
    const [anomalies, setAnomalies] = useState<{ entity: string; change_pct: number; current_revenue: number }[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [materialChartView, setMaterialChartView] = useState<"donut" | "bar">("donut");
    /** Draft inputs for sales targets (saved to Postgres via API) */
    const [draftRevenue, setDraftRevenue] = useState("");
    const [draftOrders, setDraftOrders] = useState("");
    const [savingTargets, setSavingTargets] = useState(false);
    const [targetError, setTargetError] = useState<string | null>(null);
    const [refreshKey, setRefreshKey] = useState(0);
    const [showInstructions, setShowInstructions] = useState(false);
    const migratedLocalTargets = React.useRef(false);

    /** One-time migration: browser-only targets → database */
    React.useEffect(() => {
        if (migratedLocalTargets.current) return;
        const r = localStorage.getItem("elettro_goal_revenue");
        const o = localStorage.getItem("elettro_goal_orders");
        if (!r && !o) return;
        migratedLocalTargets.current = true;
        (async () => {
            try {
                await saveSalesTargets({
                    tenant_id: tenant,
                    target_revenue: r ? Number(r) : null,
                    target_orders: o ? Number(o) : null,
                });
                localStorage.removeItem("elettro_goal_revenue");
                localStorage.removeItem("elettro_goal_orders");
                setRefreshKey((k) => k + 1);
            } catch {
                migratedLocalTargets.current = false;
            }
        })();
    }, [tenant]);

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
                items: selectedItems.length > 0 ? selectedItems.join(',') : undefined,
            };

            const anomalyParams = {
                tenant,
                startDate: p.startDate,
                endDate: p.endDate,
                states: selectedStates.length > 0 ? selectedStates.join(",") : undefined,
                customers: selectedCustomers.length > 0 ? selectedCustomers.join(",") : undefined,
                materialGroups: selectedMaterialGroups.length > 0 ? selectedMaterialGroups.join(",") : undefined,
                fiscalYears: selectedFiscalYears.length > 0 ? selectedFiscalYears.join(",") : undefined,
                months: selectedMonths.length > 0 ? selectedMonths.join(",") : undefined,
                items: selectedItems.length > 0 ? selectedItems.join(",") : undefined,
                dropThresholdPct: 20,
            };

            setLoadError(null);
            const anomPromise = fetchAnomalies(anomalyParams);

            try {
                // Prefer single dashboard call (fastest). If it errors in prod, fallback to individual endpoints.
                const res = await fetchDashboardSummary(p);
                const anom = await anomPromise;

                if (res?.message && String(res.message).toLowerCase().includes("backend error")) {
                    throw new Error(String(res.message));
                }

                if (res) {
                    setData({
                        summary: res.summary ?? null,
                        trend: res.trend ?? [],
                        materials: res.material_groups ?? [],
                        customers: res.top_customers ?? [],
                        comparison: res.comparison ?? null,
                        goals: res.goals ?? null,
                        sales_targets: res.sales_targets ?? null,
                        message: res.message ?? null,
                    });
                    const st = res.sales_targets;
                    if (st) {
                        setDraftRevenue(st.revenue != null ? String(st.revenue) : "");
                        setDraftOrders(st.orders != null ? String(st.orders) : "");
                    }
                } else {
                    setData({ summary: null, trend: [], materials: [], customers: [], comparison: null, goals: null, sales_targets: null, message: null });
                    setLoadError("No data returned. Check API URL and that data is uploaded.");
                }
                setAnomalies(anom?.anomalies ?? []);
            } catch (e) {
                console.error("Failed to fetch dashboard summary; falling back to individual endpoints", e);
                try {
                    const [kpi, trend, materials, customers, anom] = await Promise.all([
                        fetchKpiSummary(p),
                        fetchSalesTrend(p),
                        fetchMaterialGroups(p),
                        fetchTopCustomers(p),
                        anomPromise,
                    ]);

                    setData({
                        summary: kpi ? { revenue: kpi.revenue ?? 0, orders: kpi.orders ?? 0, customers: kpi.customers ?? 0, average_order_value: kpi.average_order_value ?? 0 } : null,
                        trend: Array.isArray(trend) ? trend : [],
                        materials: Array.isArray(materials) ? materials : [],
                        customers: Array.isArray(customers) ? customers : [],
                        comparison: null,
                        goals: null,
                        sales_targets: null,
                        message: null,
                    });
                    setAnomalies(anom?.anomalies ?? []);
                    setLoadError("Dashboard summary endpoint failed; loaded via fallback (slower).");
                } catch (e2) {
                    const msg = e2 instanceof Error ? e2.message : String(e2);
                    if (msg.includes("502") || msg.includes("Bad Gateway")) {
                        setLoadError("Backend unreachable (502). If using Render free tier, the service may be sleeping — wait 30–60s and retry.");
                    } else if (msg.includes("abort") || msg.includes("timeout") || msg.includes("fetch")) {
                        setLoadError("Backend is slow or unreachable (e.g. cold start). Please retry in a moment.");
                    } else {
                        setLoadError(msg || "Failed to load data. Please retry.");
                    }
                    setData({ summary: null, trend: [], materials: [], customers: [], comparison: null, goals: null, sales_targets: null, message: null });
                    setAnomalies([]);
                }
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems, refreshKey]);

    const handleSaveSalesTargets = async () => {
        setSavingTargets(true);
        setTargetError(null);
        try {
            const rev = draftRevenue.trim() === "" ? null : Number(draftRevenue.replace(/,/g, ""));
            const ord = draftOrders.trim() === "" ? null : parseInt(draftOrders.replace(/,/g, ""), 10);
            if (rev != null && (Number.isNaN(rev) || rev < 0)) {
                setTargetError("Revenue target must be a non-negative number.");
                return;
            }
            if (ord != null && (Number.isNaN(ord) || ord < 0)) {
                setTargetError("Orders target must be a non-negative integer.");
                return;
            }
            await saveSalesTargets({
                tenant_id: tenant,
                target_revenue: rev,
                target_orders: ord,
            });
            setRefreshKey((k) => k + 1);
        } catch (e) {
            setTargetError(e instanceof Error ? e.message : "Could not save sales targets.");
        } finally {
            setSavingTargets(false);
        }
    };

    const fmt = formatAmount;
    const sum = data.summary || { revenue: 0, orders: 0, customers: 0, average_order_value: 0 };
    const comp = data.comparison || null;
    const goals = data.goals || null;

    const validTrend = Array.isArray(data.trend) ? data.trend : [];
    const validMat = Array.isArray(data.materials) ? data.materials : [];
    const validCust = Array.isArray(data.customers) ? data.customers : [];

    const tableMat = React.useMemo(() => {
        return validMat.map((m: any) => {
            const nameKey =
                (["ITEM_NAME_GROUP", "MATERIALGROUP"].find((k) => k in m) as string | undefined) ||
                Object.keys(m).find((k) => !MATERIAL_META.has(k) && k !== "AMOUNT") ||
                "name";
            return {
                name: m[nameKey] ?? "Unknown",
                AMOUNT: m.AMOUNT,
                SHARE_PCT: m.SHARE_PCT,
                TARGET_REVENUE: m.TARGET_REVENUE,
                VS_TARGET_PCT: m.VS_TARGET_PCT,
            };
        });
    }, [validMat]);

    const materialChartNameKey = React.useMemo(() => {
        if (!validMat.length) return "name";
        const row = validMat[0] as Record<string, unknown>;
        if ("ITEM_NAME_GROUP" in row) return "ITEM_NAME_GROUP";
        if ("MATERIALGROUP" in row) return "MATERIALGROUP";
        return Object.keys(row).find((k) => !MATERIAL_META.has(k as string) && k !== "AMOUNT") || "name";
    }, [validMat]);

    const hasRevenueTargetSplit = Boolean(
        goals?.revenue_target &&
            validCust.length > 0 &&
            validCust[0]?.SHARE_PCT != null &&
            validCust[0]?.SHARE_PCT !== undefined
    );

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between flex-wrap p-4 bg-app-card border border-app-border rounded-xl">
                <div>
                    <div className="flex items-center gap-3">
                        <h2 className="text-xl font-semibold text-app-fg">Executive Summary</h2>
                        <button
                            type="button"
                            onClick={() => setShowInstructions(v => !v)}
                            className="flex items-center gap-1 text-xs text-app-fg-muted hover:text-app-gold transition-colors px-2 py-1 rounded-md hover:bg-app-muted"
                        >
                            {showInstructions ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                            {showInstructions ? "Hide guide" : "How targets work"}
                        </button>
                    </div>
                    {showInstructions && (
                        <div className="mt-2 space-y-1.5 animate-slide-down">
                            <p className="text-xs text-app-fg-muted max-w-3xl">
                                <strong className="text-app-fg">Month or year?</strong> The app stores one revenue and one orders figure per tenant — compared to{" "}
                                <strong className="text-app-fg">actual sales for your current filters</strong> (date range, months, fiscal year, etc. above). Fiscal year runs <strong className="text-app-fg">April–March</strong>. Set filters to the period you care about, then enter targets that match <em>that</em> period.
                            </p>
                            <p className="text-xs text-app-fg-muted max-w-3xl">
                                Tables below split the revenue target by <strong className="text-app-fg">each row’s % of filtered total</strong> (customers and material groups).
                            </p>
                        </div>
                    )}
                </div>
                <div className="flex flex-wrap items-end gap-3 w-full sm:w-auto">
                    <label className="flex flex-col gap-1 text-xs text-app-fg-muted min-w-[140px]">
                        Revenue target (₹)
                        <input
                            type="text"
                            inputMode="decimal"
                            value={draftRevenue}
                            onChange={(e) => setDraftRevenue(e.target.value)}
                            placeholder="e.g. 50000000"
                            className="bg-app-bg border border-app-border rounded-lg px-3 py-2 text-sm text-app-fg w-full sm:w-40 placeholder:text-app-fg-muted"
                        />
                    </label>
                    <label className="flex flex-col gap-1 text-xs text-app-fg-muted min-w-[120px]">
                        Orders target
                        <input
                            type="text"
                            inputMode="numeric"
                            value={draftOrders}
                            onChange={(e) => setDraftOrders(e.target.value)}
                            placeholder="e.g. 1200"
                            className="bg-app-bg border border-app-border rounded-lg px-3 py-2 text-sm text-app-fg w-full sm:w-32 placeholder:text-app-fg-muted"
                        />
                    </label>
                    <button
                        type="button"
                        onClick={handleSaveSalesTargets}
                        disabled={savingTargets || loading}
                        className="px-4 py-2 rounded-lg text-sm font-medium bg-app-gold text-app-on-gold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {savingTargets ? "Saving…" : "Save targets"}
                    </button>
                </div>
                {targetError && (
                    <p className="text-sm text-red-400 mt-2">{targetError}</p>
                )}
            </div>
            {loadError && (
                <div className="p-4 bg-red-900/20 border border-red-700 rounded-xl">
                    <h3 className="text-sm font-semibold text-red-400 flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4" /> {loadError}
                    </h3>
                    <button type="button" onClick={() => setRefreshKey((k) => k + 1)} className="text-sm font-medium text-app-gold hover:underline">Retry</button>
                </div>
            )}
            {!loading && !loadError && (!data.summary || (data.summary.revenue === 0 && data.summary.orders === 0 && validTrend.length === 0 && validMat.length === 0 && validCust.length === 0)) && (
                <div className="p-4 bg-amber-900/20 border border-amber-700 rounded-xl">
                    <h3 className="text-sm font-semibold text-amber-400 flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4" /> No data for this view
                    </h3>
                    {data.message && (
                        <p className="text-sm text-amber-200/90 mb-3 font-medium">{data.message}</p>
                    )}
                    <ul className="text-sm text-app-fg space-y-1 list-disc list-inside mb-3">
                        <li>If you applied filters (e.g. <strong>FY</strong>, State, Date range), try <strong>Clear all filters</strong> or <strong>All Time</strong>.</li>
                        <li>Ensure <code className="bg-app-bg px-1 rounded">NEXT_PUBLIC_API_URL</code> points to your Render backend in Vercel env vars, then <strong>redeploy</strong>.</li>
                        <li>Upload data via <strong><Link href="/data" className="text-app-gold hover:underline">Data / Cloud Data Uploader</Link></strong> (Excel/CSV with DATE, INVOICE_NO, CUSTOMER_NAME, AMOUNT).</li>
                    </ul>
                    <button type="button" onClick={() => setRefreshKey((k) => k + 1)} className="text-sm font-medium text-app-gold hover:underline">Retry</button>
                </div>
            )}
            {anomalies.length > 0 && (
                <div className="p-4 bg-red-900/20 border border-red-800 rounded-xl">
                    <h3 className="text-sm font-semibold text-red-400 flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4" /> Revenue drop vs previous period (&gt;20%)
                    </h3>
                    <ul className="text-sm text-app-fg space-y-1">
                        {anomalies.slice(0, 5).map((a) => (
                            <li key={a.entity}>
                                <span className="font-medium text-app-fg">{a.entity}</span>
                                <span className="text-red-400 ml-2">{a.change_pct}%</span>
                            </li>
                        ))}
                        {anomalies.length > 5 && <li className="text-app-fg-muted">+{anomalies.length - 5} more</li>}
                    </ul>
                </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <KpiCard
                    animationDelay={0}
                    title="Total Revenue"
                    value={loading || !data.summary ? "—" : fmt(sum.revenue)}
                    icon={IndianRupee}
                    trend={comp ? `${comp.revenue_pct >= 0 ? "+" : ""}${comp.revenue_pct}%` : undefined}
                    trendUp={comp ? comp.revenue_pct >= 0 : undefined}
                    goalPct={goals?.revenue_achievement_pct}
                    targetLabel={goals?.revenue_target != null ? `Target ${fmt(goals.revenue_target)}` : undefined}
                />
                <KpiCard
                    animationDelay={50}
                    title="Total Orders"
                    value={loading || !data.summary ? "—" : sum.orders.toLocaleString()}
                    icon={ShoppingCart}
                    trend={comp ? `${comp.orders_pct >= 0 ? "+" : ""}${comp.orders_pct}%` : undefined}
                    trendUp={comp ? comp.orders_pct >= 0 : undefined}
                    goalPct={goals?.orders_achievement_pct}
                    targetLabel={goals?.orders_target != null ? `Target ${goals.orders_target.toLocaleString()} orders` : undefined}
                />
                <KpiCard
                    animationDelay={100}
                    title="Active Customers"
                    value={loading || !data.summary ? "—" : sum.customers.toLocaleString()}
                    icon={Users}
                    trend={comp ? `${comp.customers_pct >= 0 ? "+" : ""}${comp.customers_pct}%` : undefined}
                    trendUp={comp ? comp.customers_pct >= 0 : undefined}
                />
                <KpiCard
                    animationDelay={150}
                    title="Avg Order Value"
                    value={loading || !data.summary ? "—" : fmt(sum.average_order_value)}
                    icon={TrendingUp}
                    trend={comp ? `${comp.average_order_value_pct >= 0 ? "+" : ""}${comp.average_order_value_pct}%` : undefined}
                    trendUp={comp ? comp.average_order_value_pct >= 0 : undefined}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 bg-app-card border border-app-border rounded-xl p-6 min-h-[420px] flex flex-col animate-fade-in opacity-0 animation-delay-200">
                    <div className="border-l-4 border-app-gold pl-3 mb-4">
                        <h3 className="text-lg font-semibold text-app-fg">Monthly Sales Trend</h3>
                        <p className="text-sm text-app-fg-muted mt-0.5">Revenue over the selected period</p>
                    </div>
                    {loading ? (
                        <div className="flex-1 min-h-[320px] rounded-lg bg-app-bg/50 animate-pulse flex items-center justify-center border border-app-border/50">
                            <span className="text-app-fg-muted text-sm">Loading chart...</span>
                        </div>
                    ) : (
                        <div className="flex-1 min-h-[320px]">
                            <GradientAreaChart data={validTrend} xKey="DATE" yKey="AMOUNT" formatCurrency={true} />
                        </div>
                    )}
                </div>

                <div className="bg-app-card border border-app-border rounded-xl p-6 min-h-[420px] flex flex-col animate-fade-in opacity-0 animation-delay-300">
                    <div className="border-l-4 border-app-gold pl-3 mb-4 flex items-center justify-between flex-wrap gap-2">
                        <div>
                            <h3 className="text-lg font-semibold text-app-fg">Top Material Groups</h3>
                            <p className="text-sm text-app-fg-muted mt-0.5">By revenue share</p>
                        </div>
                        <div className="flex rounded-lg border border-app-border p-0.5 bg-app-bg">
                            <button type="button" onClick={() => setMaterialChartView("donut")} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${materialChartView === "donut" ? "bg-app-gold text-app-on-gold font-medium" : "text-app-fg-muted hover:text-app-fg"}`}>Donut</button>
                            <button type="button" onClick={() => setMaterialChartView("bar")} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${materialChartView === "bar" ? "bg-app-gold text-app-on-gold font-medium" : "text-app-fg-muted hover:text-app-fg"}`}>Bar</button>
                        </div>
                    </div>
                    {loading ? (
                        <div className="flex-1 min-h-[320px] rounded-lg bg-app-bg/50 animate-pulse flex items-center justify-center border border-app-border/50">
                            <span className="text-app-fg-muted text-sm">Loading chart...</span>
                        </div>
                    ) : (
                        <div className="flex-1 min-h-[320px]">
                            {materialChartView === "bar" ? (
                                <CategoryHorizontalBarChart data={validMat} nameKey={materialChartNameKey} valueKey="AMOUNT" />
                            ) : (
                                <InteractiveDonutChart data={validMat} nameKey={materialChartNameKey} valueKey="AMOUNT" />
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
                {/* Top Customers Table */}
                <div className="bg-app-card border border-app-border rounded-xl p-6 flex flex-col animate-fade-in opacity-0 animation-delay-400">
                    <h3 className="text-lg font-semibold text-app-fg mb-1 border-b border-app-border pb-4">Top Customers</h3>
                    {hasRevenueTargetSplit && (
                        <p className="text-xs text-app-fg-muted mb-3 -mt-2">Share % = row revenue ÷ total filtered revenue. Implied target = your saved revenue goal × same share.</p>
                    )}
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
                                    cell: (item: any) => <span className="text-app-fg font-bold">{fmt(item.AMOUNT)}</span>
                                },
                                ...(hasRevenueTargetSplit
                                    ? [
                                          {
                                              header: 'Share %',
                                              accessorKey: 'SHARE_PCT',
                                              sortable: true,
                                              align: 'right' as const,
                                              cell: (item: any) => (
                                                  <span className="text-app-fg-muted">{Number(item.SHARE_PCT).toFixed(1)}%</span>
                                              ),
                                          },
                                          {
                                              header: 'Implied target',
                                              accessorKey: 'TARGET_REVENUE',
                                              sortable: true,
                                              align: 'right' as const,
                                              cell: (item: any) => (
                                                  <span className="text-app-gold">{fmt(item.TARGET_REVENUE)}</span>
                                              ),
                                          },
                                          {
                                              header: '% of target',
                                              accessorKey: 'VS_TARGET_PCT',
                                              sortable: true,
                                              align: 'right' as const,
                                              cell: (item: any) => (
                                                  <span className="text-app-fg-muted">{Number(item.VS_TARGET_PCT).toFixed(0)}%</span>
                                              ),
                                          },
                                      ]
                                    : []),
                            ]}
                        />
                    </div>
                </div>

                {/* Top Material Groups Table */}
                <div className="bg-app-card border border-app-border rounded-xl p-6 flex flex-col animate-fade-in opacity-0 animation-delay-500">
                    <h3 className="text-lg font-semibold text-app-fg mb-1 border-b border-app-border pb-4">Top Performers (Material Groups)</h3>
                    {hasRevenueTargetSplit && (
                        <p className="text-xs text-app-fg-muted mb-3 -mt-2">Same split rule as customers: each group’s % of total sales × your revenue goal.</p>
                    )}
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
                                    cell: (item: any) => <span className="text-app-fg font-bold">{fmt(item.AMOUNT)}</span>
                                },
                                ...(hasRevenueTargetSplit
                                    ? [
                                          {
                                              header: 'Share %',
                                              accessorKey: 'SHARE_PCT',
                                              sortable: true,
                                              align: 'right' as const,
                                              cell: (item: any) => (
                                                  <span className="text-app-fg-muted">{Number(item.SHARE_PCT).toFixed(1)}%</span>
                                              ),
                                          },
                                          {
                                              header: 'Implied target',
                                              accessorKey: 'TARGET_REVENUE',
                                              sortable: true,
                                              align: 'right' as const,
                                              cell: (item: any) => (
                                                  <span className="text-app-gold">{fmt(item.TARGET_REVENUE)}</span>
                                              ),
                                          },
                                          {
                                              header: '% of target',
                                              accessorKey: 'VS_TARGET_PCT',
                                              sortable: true,
                                              align: 'right' as const,
                                              cell: (item: any) => (
                                                  <span className="text-app-fg-muted">{Number(item.VS_TARGET_PCT).toFixed(0)}%</span>
                                              ),
                                          },
                                      ]
                                    : []),
                            ]}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
