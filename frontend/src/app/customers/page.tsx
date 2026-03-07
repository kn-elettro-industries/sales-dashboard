"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import { useFilter } from "@/components/FilterContext";
import { fetchAllCustomers, fetchRfmSegments } from "@/lib/api";
import { Users, Crown, AlertTriangle, UserX } from "lucide-react";
import { KpiCard } from "@/components/ui/KpiCard";
import { DataTable } from "@/components/ui/DataTable";
import { ScatterBubbleChart } from "@/components/ui/Charts";
import { formatAmount } from "@/lib/format";

const SEGMENT_COLORS: Record<string, string> = {
    "Champions": "bg-green-600",
    "Loyal": "bg-blue-600",
    "Potential": "bg-yellow-600",
    "At Risk": "bg-orange-600",
    "Lost": "bg-red-600",
};

export default function CustomersPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths } = useFilter();
    const [data, setData] = useState<any>({ customers: [], rfm: [] });
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
                const [customers, rfm] = await Promise.all([
                    fetchAllCustomers(p).catch(() => []),
                    fetchRfmSegments(p).catch(() => []),
                ]);
                setData({ customers, rfm });
            } catch (e) {
                console.error("Failed to fetch customer data", e);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths]);

    const validCustomers = Array.isArray(data.customers) ? data.customers : [];
    const validRfm = Array.isArray(data.rfm) ? data.rfm : [];
    const fmt = formatAmount;

    const segCounts: Record<string, number> = {};
    validRfm.forEach((r: any) => { segCounts[r.Segment] = (segCounts[r.Segment] || 0) + 1; });

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            <div>
                <h2 className="text-2xl font-bold text-white">Customer Intelligence</h2>
                <p className="text-gray-400 mt-1">RFM segmentation and customer analysis.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <KpiCard title="Total Customers" value={validCustomers.length.toString()} icon={Users} />
                <KpiCard title="Champions" value={(segCounts["Champions"] || 0).toString()} icon={Crown} />
                <KpiCard title="At Risk" value={(segCounts["At Risk"] || 0).toString()} icon={AlertTriangle} />
                <KpiCard title="Lost" value={(segCounts["Lost"] || 0).toString()} icon={UserX} />
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">Customer Segments</h3>
                <div className="flex gap-3 flex-wrap">
                    {Object.entries(segCounts).length > 0 ? Object.entries(segCounts).map(([seg, count]) => (
                        <div key={seg} className={`${SEGMENT_COLORS[seg] || 'bg-gray-600'} rounded-lg px-4 py-3 text-center min-w-[120px]`}>
                            <div className="text-2xl font-bold text-white">{count}</div>
                            <div className="text-sm text-white/80">{seg}</div>
                        </div>
                    )) : <div className="text-gray-500">No segmented customers found in this period.</div>}
                </div>
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4">RFM Customer Map</h3>
                {validRfm.length > 0 ? (
                    <ScatterBubbleChart data={validRfm} xKey="Recency" yKey="Frequency" zKey="Monetary" nameKey="CUSTOMER_NAME" />
                ) : (
                    <div className="h-40 flex items-center justify-center text-gray-500">No data</div>
                )}
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">RFM Analysis</h3>
                <DataTable
                    data={validRfm}
                    searchable={true}
                    searchPlaceholder="Search customers..."
                    searchKeys={['CUSTOMER_NAME']}
                    pageSizeOptions={[10, 25, 50]}
                    defaultPageSize={10}
                    columns={[
                        { header: 'Customer', accessorKey: 'CUSTOMER_NAME', sortable: true },
                        { header: 'Recency (days)', accessorKey: 'Recency', sortable: true, align: 'right' },
                        { header: 'Frequency', accessorKey: 'Frequency', sortable: true, align: 'right' },
                        {
                            header: 'Revenue',
                            accessorKey: 'Monetary',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-white font-semibold">{fmt(item.Monetary)}</span>
                        },
                        {
                            header: 'Segment',
                            accessorKey: 'Segment',
                            sortable: true,
                            align: 'center',
                            cell: (item: any) => (
                                <span className={`${SEGMENT_COLORS[item.Segment] || 'bg-gray-600'} text-white text-xs px-2 py-1 rounded-full`}>
                                    {item.Segment}
                                </span>
                            )
                        }
                    ]}
                />
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">Top Customers by Revenue</h3>
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
                            cell: (_, index) => <span className="text-gray-500">{index! + 1}</span> // Fixed index rendering
                        },
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
                            header: 'Avg Order',
                            accessorKey: 'AvgOrder',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span>{fmt(item.AvgOrder)}</span>
                        },
                        { header: 'Last Order', accessorKey: 'LastOrder', sortable: true, align: 'right' }
                    ]}
                />
            </div>
        </div>
    );
}
