
"use client";

import React, { useEffect, useState, useMemo } from "react";
import { format } from "date-fns";
import { useFilter } from "@/components/FilterContext";
import { fetchStateData, fetchCityData } from "@/lib/api";
import { BarChart } from "@/components/ui/Charts";
import { KpiCard } from "@/components/ui/KpiCard";
import { DataTable } from "@/components/ui/DataTable";
import { MapPin, Building2, Globe, TrendingUp, ChevronLeft } from "lucide-react";
import { formatAmount, formatCr } from "@/lib/format";
import dynamic from "next/dynamic";

// Lazy load the map (SSR incompatible)
const IndiaMap = dynamic(() => import("@/components/ui/IndiaMap"), { ssr: false });

export default function GeographicPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths } = useFilter();
    const [data, setData] = useState<any>({ states: [], cities: [] });
    const [loading, setLoading] = useState(true);
    const [drilldownState, setDrilldownState] = useState<string | null>(null);

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
                const [states, cities] = await Promise.all([
                    fetchStateData(p).catch(() => []),
                    fetchCityData(p).catch(() => []),
                ]);
                setData({ states, cities });
            } catch (e) {
                console.error("Failed to fetch geographic data", e);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths]);

    const validStates = Array.isArray(data.states) ? data.states : [];
    const validCities = Array.isArray(data.cities) ? data.cities : [];

    const tableCities = React.useMemo(() => {
        return validCities.map((c: any) => {
            const cityKey = Object.keys(c).find(k => !['Revenue', 'Customers'].includes(k)) || 'CITY';
            return {
                ...c,
                CityName: c[cityKey] || 'Unknown'
            };
        });
    }, [validCities]);

    const fmt = formatAmount;
    const fmtCrVal = formatCr;

    const topState = validStates.length > 0 ? validStates[0] : null;
    const totalRevenue = validStates.reduce((sum: number, s: any) => sum + (s.Revenue || 0), 0);

    // Drilldown data
    const drilldownData = drilldownState
        ? validCities.filter((c: any) => {
            // If cities have state info, filter by state. Otherwise show all.
            return true;
        })
        : [];

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            <div>
                <h2 className="text-2xl font-bold text-white">Geographic Intelligence</h2>
                <p className="text-gray-400 mt-1">Interactive map with state and city level revenue analysis.</p>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <KpiCard title="Active States" value={validStates.length.toString()} icon={Globe} />
                <KpiCard title="Active Cities" value={validCities.length.toString()} icon={Building2} />
                <KpiCard title="Top State" value={topState?.STATE || 'N/A'} icon={MapPin} />
                <KpiCard title="Avg Revenue/State" value={validStates.length > 0 ? fmtCrVal(totalRevenue / validStates.length) : '₹ 0'} icon={TrendingUp} />
            </div>

            {/* Interactive National Map */}
            {!drilldownState && (
                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">
                        National Sales Map
                        <span className="text-sm font-normal text-gray-400 ml-2">Click a state to view details</span>
                    </h3>
                    {validStates.length > 0 ? (
                        <IndiaMap
                            states={validStates}
                            onStateClick={(stateName) => setDrilldownState(stateName)}
                        />
                    ) : (
                        <div className="h-80 flex items-center justify-center text-gray-500">No geographic data available</div>
                    )}
                </div>
            )}

            {/* State Drilldown View */}
            {drilldownState && (
                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                    <div className="flex items-center justify-between border-b border-[#30363d] pb-4 mb-4">
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setDrilldownState(null)}
                                className="flex items-center text-sm text-[#daa520] hover:underline"
                            >
                                <ChevronLeft className="h-4 w-4 mr-1" />
                                Back to National View
                            </button>
                            <h3 className="text-lg font-semibold text-white">
                                {drilldownState} — State Details
                            </h3>
                        </div>
                    </div>

                    {(() => {
                        const stateInfo = validStates.find((s: any) => s.STATE === drilldownState);
                        if (!stateInfo) return <div className="text-gray-500">No data for this state</div>;
                        return (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-4">
                                    <div className="text-xs text-gray-500 uppercase mb-1">State Revenue</div>
                                    <div className="text-xl font-bold text-white">{fmtCrVal(stateInfo.Revenue)}</div>
                                </div>
                                <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-4">
                                    <div className="text-xs text-gray-500 uppercase mb-1">Market Share</div>
                                    <div className="text-xl font-bold text-[#daa520]">{stateInfo.MarketShare ?? 0}%</div>
                                </div>
                                <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-4">
                                    <div className="text-xs text-gray-500 uppercase mb-1">Total Orders</div>
                                    <div className="text-xl font-bold text-white">{stateInfo.Orders?.toLocaleString()}</div>
                                </div>
                            </div>
                        );
                    })()}
                </div>
            )}

            {/* State Revenue Rankings */}
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4">
                    State Revenue Rankings
                </h3>
                {validStates.length > 0 ? (
                    <BarChart data={validStates.slice(0, 15)} xKey="STATE" yKey="Revenue" />
                ) : (
                    <div className="h-80 flex items-center justify-center text-gray-500">No geographic data</div>
                )}
            </div>

            {/* Tables Side by Side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 flex flex-col">
                    <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">State Breakdown</h3>
                    <div className="flex-1 min-h-[400px]">
                        <DataTable
                            data={validStates}
                            searchable={true}
                            searchPlaceholder="Search states..."
                            searchKeys={['STATE']}
                            pageSizeOptions={[5, 10, 20]}
                            defaultPageSize={10}
                            onRowClick={(item) => setDrilldownState(item.STATE)}
                            columns={[
                                { header: 'State', accessorKey: 'STATE', sortable: true },
                                {
                                    header: 'Revenue',
                                    accessorKey: 'Revenue',
                                    sortable: true,
                                    align: 'right',
                                    cell: (item: any) => <span className="text-white font-semibold">{fmt(item.Revenue)}</span>
                                },
                                {
                                    header: 'Share %',
                                    accessorKey: 'MarketShare',
                                    sortable: true,
                                    align: 'right',
                                    cell: (item: any) => <span className="text-[#daa520]">{item.MarketShare}%</span>
                                },
                                { header: 'Orders', accessorKey: 'Orders', sortable: true, align: 'right' }
                            ]}
                        />
                    </div>
                </div>

                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 flex flex-col">
                    <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">Top Cities</h3>
                    <div className="flex-1 min-h-[400px]">
                        <DataTable
                            data={tableCities}
                            searchable={true}
                            searchPlaceholder="Search cities..."
                            searchKeys={['CityName']}
                            pageSizeOptions={[5, 10, 20]}
                            defaultPageSize={10}
                            columns={[
                                { header: 'City', accessorKey: 'CityName', sortable: true },
                                {
                                    header: 'Revenue',
                                    accessorKey: 'Revenue',
                                    sortable: true,
                                    align: 'right',
                                    cell: (item: any) => <span className="text-white font-semibold">{fmt(item.Revenue)}</span>
                                },
                                { header: 'Customers', accessorKey: 'Customers', sortable: true, align: 'right' }
                            ]}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
