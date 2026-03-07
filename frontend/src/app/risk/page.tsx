"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import { useFilter } from "@/components/FilterContext";
import { fetchAllCustomers } from "@/lib/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { ShieldAlert, AlertTriangle, TrendingDown, Users } from "lucide-react";
import { formatAmount } from "@/lib/format";
import { DataTable } from "@/components/ui/DataTable";

export default function RiskPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths } = useFilter();
    const [data, setData] = useState<any>({ customers: [] });
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
                const [customers] = await Promise.all([
                    fetchAllCustomers(p).catch(() => []),
                ]);
                setData({ customers });
            } catch (e) {
                console.error("Failed to fetch risk data", e);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths]);

    const validCustomers = Array.isArray(data.customers) ? data.customers : [];
    const fmt = formatAmount;

    const totalRev = validCustomers.reduce((s: number, c: any) => s + (c.Revenue || 0), 0);
    const top3Rev = validCustomers.slice(0, 3).reduce((s: number, c: any) => s + (c.Revenue || 0), 0);
    const top3Pct = totalRev > 0 ? (top3Rev / totalRev * 100).toFixed(1) : 0;

    const singleOrderCustomers = validCustomers.filter((c: any) => c.Orders <= 1);
    const inactiveCustomers = validCustomers.filter((c: any) => {
        if (!c.LastOrder) return false;
        const diffDays = (Date.now() - new Date(c.LastOrder).getTime()) / (1000 * 60 * 60 * 24);
        return diffDays > 90;
    });

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            <div>
                <h2 className="text-2xl font-bold text-white">Risk Management</h2>
                <p className="text-gray-400 mt-1">Concentration risk, churn risk, and operational alerts.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <KpiCard title="Revenue Concentration" value={`Top 3: ${top3Pct}%`} icon={ShieldAlert} />
                <KpiCard title="Single-Order Customers" value={singleOrderCustomers.length.toString()} icon={AlertTriangle} />
                <KpiCard title="Inactive (90+ days)" value={inactiveCustomers.length.toString()} icon={TrendingDown} />
                <KpiCard title="Total Customers" value={validCustomers.length.toString()} icon={Users} />
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">Revenue Concentration Risk</h3>
                <DataTable
                    data={validCustomers}
                    searchable={true}
                    searchPlaceholder="Search customers..."
                    searchKeys={['CUSTOMER_NAME']}
                    pageSizeOptions={[10, 25, 50]}
                    defaultPageSize={10}
                    columns={[
                        {
                            header: '#',
                            accessorKey: '_index',
                            sortable: false,
                            align: 'center',
                            cell: (_, index) => <span className="text-gray-500">{index! + 1}</span>
                        },
                        { header: 'Customer', accessorKey: 'CUSTOMER_NAME', sortable: true },
                        {
                            header: 'Concentration',
                            accessorKey: 'pct',
                            sortable: false,
                            cell: (item: any) => {
                                const pct = totalRev > 0 ? (item.Revenue / totalRev * 100) : 0;
                                return (
                                    <div className="flex items-center gap-3 w-48">
                                        <div className="flex-1 bg-[#2d333b] rounded-full h-2.5 overflow-hidden">
                                            <div className="bg-[#daa520] h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%` }}></div>
                                        </div>
                                        <span className="text-gray-300 text-xs w-10 text-right">{pct.toFixed(1)}%</span>
                                    </div>
                                );
                            }
                        },
                        {
                            header: 'Revenue',
                            accessorKey: 'Revenue',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-white font-semibold">{fmt(item.Revenue)}</span>
                        }
                    ]}
                />
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">Inactive Customers (90+ Days)</h3>
                <DataTable
                    data={inactiveCustomers}
                    searchable={true}
                    searchPlaceholder="Search inactive customers..."
                    searchKeys={['CUSTOMER_NAME']}
                    pageSizeOptions={[10, 25]}
                    defaultPageSize={10}
                    columns={[
                        { header: 'Customer', accessorKey: 'CUSTOMER_NAME', sortable: true },
                        {
                            header: 'Revenue',
                            accessorKey: 'Revenue',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-white font-semibold">{fmt(item.Revenue)}</span>
                        },
                        { header: 'Orders', accessorKey: 'Orders', sortable: true, align: 'right' },
                        {
                            header: 'Last Order',
                            accessorKey: 'LastOrder',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-red-400">{item.LastOrder}</span>
                        }
                    ]}
                />
                {inactiveCustomers.length === 0 && (
                    <p className="text-green-400 py-4 text-center mt-2">All customers are active within the last 90 days or no data exists.</p>
                )}
            </div>
        </div>
    );
}
