"use client";

import React, { useEffect, useState } from "react";
import { format } from "date-fns";
import { useFilter } from "@/components/FilterContext";
import { fetchMaterialPerformance, fetchParetoData } from "@/lib/api";
import { ModernTreemap, CategoryHorizontalBarChart } from "@/components/ui/Charts";
import { KpiCard } from "@/components/ui/KpiCard";
import { DataTable } from "@/components/ui/DataTable"; // Added this import
import { Package, Award, Layers } from "lucide-react";
import { formatAmount } from "@/lib/format";

export default function MaterialsPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems } = useFilter();
    const [revenueChartView, setRevenueChartView] = useState<"treemap" | "bar">("treemap");
    const [data, setData] = useState<any>({ performance: [], pareto: [] });
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
                items: selectedItems.length > 0 ? selectedItems.join(',') : undefined,
            };

            try {
                const [performance, pareto] = await Promise.all([
                    fetchMaterialPerformance(p).catch(() => []),
                    fetchParetoData(p).catch(() => []),
                ]);
                setData({ performance, pareto });
            } catch (e) {
                console.error("Failed to fetch material data", e);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems]);

    const validPerf = Array.isArray(data.performance) ? data.performance : [];
    const validPareto = Array.isArray(data.pareto) ? data.pareto : [];

    const tablePareto = React.useMemo(() => {
        return validPareto.map((p: any) => {
            const nameKey =
                Object.keys(p).find(k => !['AMOUNT', 'Percentage', 'Cumulative', 'Class'].includes(k)) || 'ITEM_NAME_GROUP';
            return {
                ...p,
                MaterialGroup: p.ITEM_NAME_GROUP ?? p[nameKey] ?? 'Unknown',
            };
        });
    }, [validPareto]);

    const fmt = formatAmount;

    const classA = validPareto.filter((p: any) => p.Class === "A").length;
    const classB = validPareto.filter((p: any) => p.Class === "B").length;
    const classC = validPareto.filter((p: any) => p.Class === "C").length;

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            <div>
                <h2 className="text-2xl font-bold text-app-fg">Material Performance</h2>
                <p className="text-app-fg-muted mt-1">Pareto analysis and category breakdown.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <KpiCard title="Total Categories" value={validPerf.length.toString()} icon={Package} />
                <KpiCard title="Class A (80% Revenue)" value={`${classA} items`} icon={Award} />
                <KpiCard title="Class B + C" value={`${classB + classC} items`} icon={Layers} />
            </div>

            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <div className="flex items-center justify-between flex-wrap gap-2 border-b border-app-border pb-4 mb-4">
                    <h3 className="text-lg font-semibold text-app-fg">Revenue by Material Group</h3>
                    <div className="flex rounded-lg border border-app-border p-0.5 bg-app-bg">
                        <button type="button" onClick={() => setRevenueChartView("treemap")} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${revenueChartView === "treemap" ? "bg-app-gold text-app-on-gold font-medium" : "text-app-fg-muted hover:text-app-fg"}`}>Treemap</button>
                        <button type="button" onClick={() => setRevenueChartView("bar")} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${revenueChartView === "bar" ? "bg-app-gold text-app-on-gold font-medium" : "text-app-fg-muted hover:text-app-fg"}`}>Bar</button>
                    </div>
                </div>
                {validPerf.length > 0 ? (
                    revenueChartView === "bar" ? (
                        <CategoryHorizontalBarChart data={validPerf.slice(0, 15)} nameKey={Object.keys(validPerf[0] || {}).find(k => !["Revenue", "Orders", "Customers", "AvgPrice", "Share", "CumulativeShare"].includes(k)) || "name"} valueKey="Revenue" />
                    ) : (
                        <ModernTreemap data={validPerf.slice(0, 15)} nameKey={Object.keys(validPerf[0] || {}).find(k => !["Revenue", "Orders", "Customers", "AvgPrice", "Share", "CumulativeShare"].includes(k)) || "name"} valueKey="Revenue" />
                    )
                ) : (
                    <div className="h-80 flex items-center justify-center text-app-fg-muted">No data</div>
                )}
            </div>

            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4">ABC Classification (Pareto)</h3>
                <DataTable
                    data={tablePareto}
                    searchable={true}
                    searchPlaceholder="Search materials..."
                    searchKeys={['MaterialGroup']}
                    pageSizeOptions={[10, 25, 50]}
                    defaultPageSize={10}
                    maxHeight="500px"
                    columns={[
                        {
                            header: 'Material Group',
                            accessorKey: 'MaterialGroup',
                            sortable: true,
                            cell: (item: any) => <span className="font-medium text-app-fg">{(item.MaterialGroup ?? '').slice(0, 45)}</span>
                        },
                        {
                            header: 'Revenue',
                            accessorKey: 'AMOUNT',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-app-fg font-semibold">{fmt(item.AMOUNT)}</span>
                        },
                        {
                            header: 'Share %',
                            accessorKey: 'Percentage',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-app-fg">{item.Percentage}%</span>
                        },
                        {
                            header: 'Cumulative %',
                            accessorKey: 'Cumulative',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-app-fg">{item.Cumulative}%</span>
                        },
                        {
                            header: 'Class',
                            accessorKey: 'Class',
                            sortable: true,
                            align: 'center',
                            cell: (item: any) => {
                                const classColor = item.Class === 'A' ? 'bg-green-600' : item.Class === 'B' ? 'bg-yellow-600' : 'bg-red-600';
                                return <span className={`${classColor} text-white text-xs px-3 py-1 rounded-full font-bold`}>{item.Class}</span>;
                            }
                        }
                    ]}
                />
            </div>
        </div>
    );
}
