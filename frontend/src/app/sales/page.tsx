"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import { useFilter } from "@/components/FilterContext";
import { KpiCard } from "@/components/ui/KpiCard";
import { GradientAreaChart } from "@/components/ui/Charts";
import { DataTable } from "@/components/ui/DataTable"; // Added DataTable import
import { fetchMonthlySales, fetchDailySales, fetchGrowthMetrics } from "@/lib/api";
import { TrendingUp, ArrowUpRight, ArrowDownRight, DollarSign } from "lucide-react";
import { formatAmount } from "@/lib/format";

export default function SalesPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems } = useFilter();
    const [data, setData] = useState<any>({ monthly: [], daily: [], growth: null });
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);

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

            try {
                setLoadError(null);
                const [monthly, daily, growth] = await Promise.all([
                    fetchMonthlySales(p).catch(() => []),
                    fetchDailySales(30, p).catch(() => []),
                    fetchGrowthMetrics(p).catch(() => ({ mom_growth: 0, current_month_rev: 0, prev_month_rev: 0 })),
                ]);
                setData({ monthly, daily, growth });
            } catch (e) {
                console.error("Failed to fetch sales data", e);
                setLoadError("Failed to load sales data. Please try refreshing.");
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems]);

    const fmt = formatAmount;
    const g = data.growth || { mom_growth: 0, current_month_rev: 0, prev_month_rev: 0 };

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            {loadError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">{loadError}</div>
            )}
            <div>
                <h2 className="text-2xl font-bold text-app-fg">Sales & Growth Analysis</h2>
                <p className="text-app-fg-muted mt-1">Month-over-month trends and growth indicators.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <KpiCard title="Current Month Revenue" value={fmt(g.current_month_rev)} icon={DollarSign} />
                <KpiCard title="Previous Month Revenue" value={fmt(g.prev_month_rev)} icon={DollarSign} />
                <KpiCard
                    title="Month-over-Month Growth"
                    value={`${g.mom_growth > 0 ? '+' : ''}${g.mom_growth}% `}
                    icon={g.mom_growth >= 0 ? ArrowUpRight : ArrowDownRight}
                    trend={`${Math.abs(g.mom_growth)}% `}
                    trendUp={g.mom_growth >= 0}
                />
            </div>

            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4">Monthly Revenue Trend</h3>
                {Array.isArray(data.monthly) && data.monthly.length > 0 ? (
                    <GradientAreaChart data={data.monthly} xKey="MONTH" yKey="Revenue" formatCurrency={true} />
                ) : (
                    <div className="h-80 flex items-center justify-center text-app-fg-muted">No monthly data found for this period.</div>
                )}
            </div>

            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4">Daily Revenue (Last 30 Days)</h3>
                {Array.isArray(data.daily) && data.daily.length > 0 ? (
                    <GradientAreaChart data={data.daily} xKey="DAY" yKey="Revenue" formatCurrency={true} />
                ) : (
                    <div className="h-80 flex items-center justify-center text-app-fg-muted">No daily data found for this period.</div>
                )}
            </div>

            {/* Monthly Breakdown Table */}
            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4">Monthly Breakdown</h3>
                <DataTable
                    data={(() => {
                        const rows = Array.isArray(data.monthly) ? data.monthly : [];
                        return rows.map((row: any, i: number) => {
                            const prev = rows[i - 1];
                            const growth = prev && prev.Revenue > 0
                                ? ((row.Revenue - prev.Revenue) / prev.Revenue * 100)
                                : null;
                            return { ...row, _growth: growth };
                        });
                    })()}
                    pageSizeOptions={[12, 24]}
                    defaultPageSize={12}
                    columns={[
                        { header: 'Month', accessorKey: 'MONTH', sortable: true },
                        {
                            header: 'Revenue',
                            accessorKey: 'Revenue',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-app-fg font-semibold">{fmt(item.Revenue)}</span>
                        },
                        {
                            header: 'vs Prev Month',
                            accessorKey: '_growth',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => item._growth === null
                                ? <span className="text-app-fg-muted text-xs">—</span>
                                : <span className={item._growth >= 0 ? 'text-green-400 font-semibold' : 'text-red-400 font-semibold'}>
                                    {item._growth >= 0 ? '+' : ''}{item._growth.toFixed(1)}%
                                  </span>
                        },
                        {
                            header: 'Orders',
                            accessorKey: 'Orders',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-app-fg">{item.Orders?.toLocaleString()}</span>
                        },
                        {
                            header: 'Customers',
                            accessorKey: 'Customers',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-app-fg">{item.Customers?.toLocaleString()}</span>
                        }
                    ]}
                />
            </div>
        </div>
    );
}
