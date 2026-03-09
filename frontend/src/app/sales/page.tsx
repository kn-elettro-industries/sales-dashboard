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
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths } = useFilter();
    const [data, setData] = useState<any>({ monthly: [], daily: [], growth: null });
    const [loading, setLoading] = useState(true);

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
            };

            try {
                const [monthly, daily, growth] = await Promise.all([
                    fetchMonthlySales(p).catch(() => []),
                    fetchDailySales(30, p).catch(() => []),
                    fetchGrowthMetrics(p).catch(() => ({ mom_growth: 0, current_month_rev: 0, prev_month_rev: 0 })),
                ]);
                setData({ monthly, daily, growth });
            } catch (e) {
                console.error("Failed to fetch sales data", e);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths]);

    const fmt = formatAmount;
    const g = data.growth || { mom_growth: 0, current_month_rev: 0, prev_month_rev: 0 };

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            <div>
                <h2 className="text-2xl font-bold text-white">Sales & Growth Analysis</h2>
                <p className="text-gray-400 mt-1">Month-over-month trends and growth indicators.</p>
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

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4">Monthly Revenue Trend</h3>
                {Array.isArray(data.monthly) && data.monthly.length > 0 ? (
                    <GradientAreaChart data={data.monthly} xKey="MONTH" yKey="Revenue" formatCurrency={true} />
                ) : (
                    <div className="h-80 flex items-center justify-center text-gray-500">No monthly data found for this period.</div>
                )}
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4">Daily Revenue (Last 30 Days)</h3>
                {Array.isArray(data.daily) && data.daily.length > 0 ? (
                    <GradientAreaChart data={data.daily} xKey="DAY" yKey="Revenue" formatCurrency={true} />
                ) : (
                    <div className="h-80 flex items-center justify-center text-gray-500">No daily data found for this period.</div>
                )}
            </div>

            {/* Monthly Breakdown Table */}
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">Monthly Breakdown</h3>
                <DataTable
                    data={Array.isArray(data.monthly) ? data.monthly : []}
                    pageSizeOptions={[12, 24]}
                    defaultPageSize={12}
                    columns={[
                        { header: 'Month', accessorKey: 'MONTH', sortable: false }, // Month sorting requires custom logic or parsing, disabling for simplicity
                        {
                            header: 'Revenue',
                            accessorKey: 'Revenue',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-white font-semibold">{fmt(item.Revenue)}</span>
                        },
                        {
                            header: 'Orders',
                            accessorKey: 'Orders',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-gray-300">{item.Orders?.toLocaleString()}</span>
                        },
                        {
                            header: 'Customers',
                            accessorKey: 'Customers',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-gray-300">{item.Customers?.toLocaleString()}</span>
                        }
                    ]}
                />
            </div>
        </div>
    );
}
