
"use client";

import { useEffect, useState, useMemo } from "react";
import { format } from "date-fns";
import { useFilter } from "@/components/FilterContext";
import { fetchStateData, fetchCityData, fetchAllCustomers } from "@/lib/api";
import { BarChart } from "@/components/ui/Charts";
import { KpiCard } from "@/components/ui/KpiCard";
import { DataTable } from "@/components/ui/DataTable";
import { MapPin, Building2, Globe, TrendingUp, ChevronLeft, Loader2, Users } from "lucide-react";
import { formatAmount, formatCr } from "@/lib/format";
import dynamic from "next/dynamic";

const IndiaMap = dynamic(() => import("@/components/ui/IndiaMap"), { ssr: false });

export default function GeographicPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems } = useFilter();
    const [data, setData] = useState<any>({ states: [], cities: [] });
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [drilldownState, setDrilldownState] = useState<string | null>(null);
    const [drilldownCities, setDrilldownCities] = useState<any[]>([]);
    const [drilldownCustomers, setDrilldownCustomers] = useState<any[]>([]);
    const [drilldownLoading, setDrilldownLoading] = useState(false);

    const baseParams = useMemo(() => ({
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
    }), [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems]);

    useEffect(() => {
        let cancelled = false;
        async function loadData() {
            setLoading(true);
            try {
                setLoadError(null);
                const [states, cities] = await Promise.all([
                    fetchStateData(baseParams).catch(() => []),
                    fetchCityData(baseParams).catch(() => []),
                ]);
                if (!cancelled) setData({ states, cities });
            } catch (e) {
                console.error("Failed to fetch geographic data", e);
                if (!cancelled) setLoadError("Failed to load geographic data. Please try refreshing.");
            } finally {
                if (!cancelled) setLoading(false);
            }
        }
        loadData();
        return () => { cancelled = true; };
    }, [baseParams]);

    // Fetch cities + customers for the drilled-down state
    useEffect(() => {
        if (!drilldownState) {
            setDrilldownCities([]);
            setDrilldownCustomers([]);
            return;
        }
        let cancelled = false;
        setDrilldownLoading(true);
        Promise.all([
            fetchCityData({ ...baseParams, states: drilldownState }).catch(() => []),
            fetchAllCustomers({ ...baseParams, states: drilldownState }).catch(() => []),
        ]).then(([cities, customers]) => {
            if (!cancelled) {
                setDrilldownCities(Array.isArray(cities) ? cities : []);
                setDrilldownCustomers(Array.isArray(customers) ? customers : []);
            }
        }).finally(() => { if (!cancelled) setDrilldownLoading(false); });
        return () => { cancelled = true; };
    }, [drilldownState, baseParams]);

    const validStates = Array.isArray(data.states) ? data.states : [];
    const validCities = Array.isArray(data.cities) ? data.cities : [];

    const tableCities = useMemo(() => validCities.map((c: any) => {
        const cityKey = ['CITY', 'CITY_NAME', 'CityName', 'city'].find(k => k in c) || Object.keys(c).find(k => !['Revenue', 'Customers', 'Orders'].includes(k)) || 'CITY';
        return { ...c, CityName: c[cityKey] || 'Unknown' };
    }), [validCities]);

    const drilldownTableCities = useMemo(() => drilldownCities.map((c: any) => {
        const cityKey = ['CITY', 'CITY_NAME', 'CityName', 'city'].find(k => k in c) || Object.keys(c).find(k => !['Revenue', 'Customers', 'Orders'].includes(k)) || 'CITY';
        return { ...c, CityName: c[cityKey] || 'Unknown' };
    }), [drilldownCities]);

    const fmt = formatAmount;
    const fmtCrVal = formatCr;
    const topState = validStates.length > 0 ? validStates[0] : null;
    const totalRevenue = validStates.reduce((sum: number, s: any) => sum + (s.Revenue || 0), 0);

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            {loadError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">{loadError}</div>
            )}
            <div>
                <h2 className="text-2xl font-bold text-app-fg">Geographic Intelligence</h2>
                <p className="text-app-fg-muted mt-1">Interactive map with state and city level revenue analysis.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <KpiCard title="Active States" value={validStates.length.toString()} icon={Globe} animationDelay={0} />
                <KpiCard title="Active Cities" value={validCities.length.toString()} icon={Building2} animationDelay={75} />
                <KpiCard title="Top State" value={topState?.STATE || 'N/A'} icon={MapPin} animationDelay={150} />
                <KpiCard title="Avg Revenue/State" value={validStates.length > 0 ? fmtCrVal(totalRevenue / validStates.length) : '₹ 0'} icon={TrendingUp} animationDelay={225} />
            </div>

            {!drilldownState && (
                <div className="bg-app-card border border-app-border rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4">
                        National Sales Map
                        <span className="text-sm font-normal text-app-fg-muted ml-2">Click a state to view cities &amp; customers</span>
                    </h3>
                    {validStates.length > 0 ? (
                        <IndiaMap states={validStates} onStateClick={(stateName) => setDrilldownState(stateName)} />
                    ) : (
                        <div className="h-80 flex items-center justify-center text-app-fg-muted">No geographic data available</div>
                    )}
                </div>
            )}

            {drilldownState && (() => {
                const stateInfo = validStates.find(
                    (s: any) => String(s?.STATE ?? "").toLowerCase() === String(drilldownState ?? "").toLowerCase()
                );
                return (
                    <div className="space-y-6">
                        {/* Header */}
                        <div className="bg-app-card border border-app-border rounded-xl p-6">
                            <div className="flex items-center justify-between border-b border-app-border pb-4 mb-6">
                                <div className="flex items-center gap-3">
                                    <button onClick={() => setDrilldownState(null)} className="flex items-center gap-1 text-sm text-app-gold hover:underline">
                                        <ChevronLeft className="h-4 w-4" />
                                        Back to National View
                                    </button>
                                    <span className="text-app-fg-muted">|</span>
                                    <h3 className="text-lg font-semibold text-app-fg flex items-center gap-2">
                                        <MapPin className="h-4 w-4 text-app-gold" />
                                        {drilldownState}
                                    </h3>
                                </div>
                            </div>
                            {stateInfo ? (
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div className="bg-app-bg border border-app-border rounded-xl p-5 hover:border-app-border-strong transition-colors">
                                        <div className="flex justify-between items-start">
                                            <p className="text-sm font-medium text-app-fg-muted">State Revenue</p>
                                            <div className="p-2 rounded-lg bg-app-muted border border-app-border"><TrendingUp className="h-4 w-4 text-app-gold" /></div>
                                        </div>
                                        <h3 className="text-2xl font-bold text-app-fg tracking-tight mt-4">{fmtCrVal(stateInfo.Revenue)}</h3>
                                    </div>
                                    <div className="bg-app-bg border border-app-border rounded-xl p-5 hover:border-app-border-strong transition-colors">
                                        <div className="flex justify-between items-start">
                                            <p className="text-sm font-medium text-app-fg-muted">Market Share</p>
                                            <div className="p-2 rounded-lg bg-app-muted border border-app-border"><Globe className="h-4 w-4 text-app-gold" /></div>
                                        </div>
                                        <h3 className="text-2xl font-bold text-app-gold tracking-tight mt-4">{stateInfo.MarketShare ?? 0}%</h3>
                                    </div>
                                    <div className="bg-app-bg border border-app-border rounded-xl p-5 hover:border-app-border-strong transition-colors">
                                        <div className="flex justify-between items-start">
                                            <p className="text-sm font-medium text-app-fg-muted">Total Orders</p>
                                            <div className="p-2 rounded-lg bg-app-muted border border-app-border"><Building2 className="h-4 w-4 text-app-gold" /></div>
                                        </div>
                                        <h3 className="text-2xl font-bold text-app-fg tracking-tight mt-4">{stateInfo.Orders?.toLocaleString() ?? '—'}</h3>
                                    </div>
                                </div>
                            ) : (
                                <p className="text-app-fg-muted">No state summary available.</p>
                            )}
                        </div>

                        {drilldownLoading ? (
                            <div className="h-48 flex items-center justify-center text-app-fg-muted gap-2">
                                <Loader2 className="h-5 w-5 animate-spin" />
                                Loading state data...
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Cities */}
                                <div className="bg-app-card border border-app-border rounded-xl p-6">
                                    <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4 flex items-center gap-2">
                                        <Building2 className="h-4 w-4 text-app-gold" />
                                        Cities in {drilldownState}
                                    </h3>
                                    {drilldownTableCities.length > 0 ? (
                                        <div className="space-y-4">
                                            <BarChart data={drilldownTableCities.slice(0, 10)} xKey="CityName" yKey="Revenue" />
                                            <DataTable
                                                data={drilldownTableCities}
                                                searchable={true}
                                                searchPlaceholder="Search cities..."
                                                searchKeys={['CityName']}
                                                pageSizeOptions={[5, 10]}
                                                defaultPageSize={5}
                                                columns={[
                                                    { header: 'City', accessorKey: 'CityName', sortable: true },
                                                    { header: 'Revenue', accessorKey: 'Revenue', sortable: true, align: 'right', cell: (item: any) => <span className="text-app-fg font-semibold">{fmt(item.Revenue)}</span> },
                                                    { header: 'Customers', accessorKey: 'Customers', sortable: true, align: 'right' },
                                                ]}
                                            />
                                        </div>
                                    ) : (
                                        <div className="h-48 flex items-center justify-center text-app-fg-muted">No city data for {drilldownState}</div>
                                    )}
                                </div>

                                {/* Customers */}
                                <div className="bg-app-card border border-app-border rounded-xl p-6">
                                    <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4 flex items-center gap-2">
                                        <Users className="h-4 w-4 text-app-gold" />
                                        Customers in {drilldownState}
                                    </h3>
                                    {drilldownCustomers.length > 0 ? (
                                        <DataTable
                                            data={drilldownCustomers}
                                            searchable={true}
                                            searchPlaceholder="Search customers..."
                                            searchKeys={['CUSTOMER_NAME']}
                                            pageSizeOptions={[5, 10, 20]}
                                            defaultPageSize={10}
                                            columns={[
                                                { header: 'Customer', accessorKey: 'CUSTOMER_NAME', sortable: true },
                                                { header: 'Revenue', accessorKey: 'Revenue', sortable: true, align: 'right', cell: (item: any) => <span className="text-app-fg font-semibold">{fmt(item.Revenue)}</span> },
                                                { header: 'Orders', accessorKey: 'Orders', sortable: true, align: 'right' },
                                            ]}
                                        />
                                    ) : (
                                        <div className="h-48 flex items-center justify-center text-app-fg-muted">No customers found for {drilldownState}</div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                );
            })()}

            {/* State Revenue Rankings */}
            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4">State Revenue Rankings</h3>
                {validStates.length > 0 ? (
                    <BarChart data={validStates.slice(0, 15)} xKey="STATE" yKey="Revenue" />
                ) : (
                    <div className="h-80 flex items-center justify-center text-app-fg-muted">No geographic data</div>
                )}
            </div>

            {/* Tables Side by Side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
                <div className="bg-app-card border border-app-border rounded-xl p-6 flex flex-col">
                    <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4">State Breakdown</h3>
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
                                { header: 'Revenue', accessorKey: 'Revenue', sortable: true, align: 'right', cell: (item: any) => <span className="text-app-fg font-semibold">{fmt(item.Revenue)}</span> },
                                { header: 'Share %', accessorKey: 'MarketShare', sortable: true, align: 'right', cell: (item: any) => <span className="text-app-gold">{item.MarketShare}%</span> },
                                { header: 'Orders', accessorKey: 'Orders', sortable: true, align: 'right' },
                            ]}
                        />
                    </div>
                </div>
                <div className="bg-app-card border border-app-border rounded-xl p-6 flex flex-col">
                    <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4">Top Cities</h3>
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
                                { header: 'Revenue', accessorKey: 'Revenue', sortable: true, align: 'right', cell: (item: any) => <span className="text-app-fg font-semibold">{fmt(item.Revenue)}</span> },
                                { header: 'Customers', accessorKey: 'Customers', sortable: true, align: 'right' },
                            ]}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
