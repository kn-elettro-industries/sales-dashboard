"use client";

import { useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import { useFilter } from "@/components/FilterContext";
import { fetchAllCustomers, fetchRfmSegments, getExportCustomersBelowRevenueUrl } from "@/lib/api";
import { Users, Crown, AlertTriangle, UserX, TrendingDown, LayoutGrid, Download } from "lucide-react";
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

/** RFM tiers below Loyal/Champions — weaker purchase behaviour for focused review */
const LOW_BUYER_SEGMENTS = new Set(["Potential", "At Risk", "Lost"]);

export default function CustomersPage() {
    const { dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems } = useFilter();
    const [data, setData] = useState<any>({ customers: [], rfm: [] });
    const [loading, setLoading] = useState(true);
    /** Focus tables and chart on lower-purchase customers (RFM Potential / At Risk / Lost) */
    const [buyerFocus, setBuyerFocus] = useState<"all" | "low">("all");
    /** Revenue band in ₹ lakh for CSV export (inclusive). Default 0 … 5.5 L. */
    const [minRevenueLakh, setMinRevenueLakh] = useState("0");
    const [maxRevenueLakh, setMaxRevenueLakh] = useState("5.5");
    const [exportingBelow, setExportingBelow] = useState(false);

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
    }, [dateRange, tenant, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems]);

    const validCustomers = Array.isArray(data.customers) ? data.customers : [];
    const validRfm = Array.isArray(data.rfm) ? data.rfm : [];
    const fmt = formatAmount;

    const filteredRfm = useMemo(() => {
        if (buyerFocus === "all") return validRfm;
        return validRfm.filter((r: { Segment?: string }) => r.Segment && LOW_BUYER_SEGMENTS.has(r.Segment));
    }, [validRfm, buyerFocus]);

    const segCounts = useMemo(() => {
        const src = buyerFocus === "low" ? filteredRfm : validRfm;
        const out: Record<string, number> = {};
        src.forEach((r: { Segment?: string }) => {
            if (!r.Segment) return;
            out[r.Segment] = (out[r.Segment] || 0) + 1;
        });
        return out;
    }, [validRfm, filteredRfm, buyerFocus]);

    const displayCustomers = useMemo(() => {
        if (buyerFocus === "all") return validCustomers;
        const names = new Set(
            filteredRfm.map((r: { CUSTOMER_NAME?: string }) => r.CUSTOMER_NAME).filter(Boolean) as string[]
        );
        const rows = validCustomers.filter((c: { CUSTOMER_NAME?: string }) => c.CUSTOMER_NAME && names.has(c.CUSTOMER_NAME));
        return [...rows].sort((a, b) => (Number(a.Revenue) || 0) - (Number(b.Revenue) || 0));
    }, [validCustomers, filteredRfm, buyerFocus]);

    const kpiTotal = buyerFocus === "low" ? filteredRfm.length : validCustomers.length;

    const filterParams = useMemo(
        () => ({
            tenant,
            startDate: dateRange?.from ? format(dateRange.from, "yyyy-MM-dd") : undefined,
            endDate: dateRange?.to ? format(dateRange.to, "yyyy-MM-dd") : undefined,
            states: selectedStates.length > 0 ? selectedStates.join(",") : undefined,
            cities: selectedCities.length > 0 ? selectedCities.join(",") : undefined,
            customers: selectedCustomers.length > 0 ? selectedCustomers.join(",") : undefined,
            materialGroups: selectedMaterialGroups.length > 0 ? selectedMaterialGroups.join(",") : undefined,
            fiscalYears: selectedFiscalYears.length > 0 ? selectedFiscalYears.join(",") : undefined,
            months: selectedMonths.length > 0 ? selectedMonths.join(",") : undefined,
            items: selectedItems.length > 0 ? selectedItems.join(",") : undefined,
        }),
        [
            tenant,
            dateRange,
            selectedStates,
            selectedCities,
            selectedCustomers,
            selectedMaterialGroups,
            selectedFiscalYears,
            selectedMonths,
            selectedItems,
        ]
    );

    const parseLakhToInr = (raw: string, fallback: number) => {
        const v = parseFloat(raw.replace(",", "."));
        return Number.isFinite(v) && v >= 0 ? v * 100_000 : fallback;
    };

    const handleDownloadBelowThreshold = () => {
        const minInr = parseLakhToInr(minRevenueLakh, 0);
        const maxInr = parseLakhToInr(maxRevenueLakh, 550_000);
        if (minInr > maxInr) {
            alert("Minimum (₹ lakh) must be less than or equal to maximum (₹ lakh).");
            return;
        }
        try {
            setExportingBelow(true);
            const url = getExportCustomersBelowRevenueUrl(filterParams, maxInr, minInr);
            const a = document.createElement("a");
            a.style.display = "none";
            a.href = url;
            a.setAttribute("download", "");
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                setExportingBelow(false);
            }, 150);
        } catch {
            setExportingBelow(false);
        }
    };

    return (
        <div className={`space-y-8 transition-opacity duration-300 ${loading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
            <div>
                <h2 className="text-2xl font-bold text-app-fg">Customer Intelligence</h2>
                <p className="text-app-fg-muted mt-1">RFM segmentation and customer analysis.</p>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                    <span className="text-xs text-app-fg-muted uppercase tracking-wide">Detail view</span>
                    <div className="flex rounded-lg border border-app-border p-0.5 bg-app-bg">
                        <button
                            type="button"
                            onClick={() => setBuyerFocus("all")}
                            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                                buyerFocus === "all" ? "bg-app-gold text-app-on-gold font-medium" : "text-app-fg-muted hover:text-app-fg"
                            }`}
                        >
                            <LayoutGrid className="h-3.5 w-3.5 shrink-0" />
                            All customers
                        </button>
                        <button
                            type="button"
                            onClick={() => setBuyerFocus("low")}
                            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                                buyerFocus === "low" ? "bg-app-gold text-app-on-gold font-medium" : "text-app-fg-muted hover:text-app-fg"
                            }`}
                            title="Potential, At Risk, and Lost segments — lowest revenue table first"
                        >
                            <TrendingDown className="h-3.5 w-3.5 shrink-0" />
                            Low purchase customers
                        </button>
                    </div>
                    {buyerFocus === "low" && (
                        <span className="text-xs text-app-fg-muted max-w-xl">
                            Showing RFM segments <span className="text-app-gold">Potential</span>,{" "}
                            <span className="text-app-gold">At Risk</span>, <span className="text-app-gold">Lost</span> only.
                            Revenue table is sorted with <strong className="text-app-fg">lowest spend first</strong>.
                        </span>
                    )}
                </div>
                <div className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-app-border bg-app-bg/50 px-4 py-3">
                    <div className="flex flex-wrap items-end gap-2">
                        <div className="flex flex-col gap-1">
                            <label htmlFor="min-rev-lakh" className="text-xs text-app-fg-muted">
                                From (₹ lakh)
                            </label>
                            <input
                                id="min-rev-lakh"
                                type="text"
                                inputMode="decimal"
                                value={minRevenueLakh}
                                onChange={(e) => setMinRevenueLakh(e.target.value)}
                                className="w-24 bg-app-bg border border-app-border rounded-lg px-2 py-1.5 text-sm text-app-fg outline-none focus:border-app-gold"
                                aria-describedby="export-below-help"
                            />
                        </div>
                        <span className="text-app-fg-muted text-sm pb-2">–</span>
                        <div className="flex flex-col gap-1">
                            <label htmlFor="max-rev-lakh" className="text-xs text-app-fg-muted">
                                To (₹ lakh)
                            </label>
                            <input
                                id="max-rev-lakh"
                                type="text"
                                inputMode="decimal"
                                value={maxRevenueLakh}
                                onChange={(e) => setMaxRevenueLakh(e.target.value)}
                                className="w-24 bg-app-bg border border-app-border rounded-lg px-2 py-1.5 text-sm text-app-fg outline-none focus:border-app-gold"
                                aria-describedby="export-below-help"
                            />
                        </div>
                    </div>
                    <p id="export-below-help" className="text-xs text-app-fg-muted max-w-md flex-1 min-w-[12rem]">
                        Export customers whose total revenue in the period falls between these bounds (inclusive). Same date range and global filters as the rest of the app. Revenue = sum of{" "}
                        <strong className="text-app-fg">AMOUNT</strong> only (excludes tax). Example: 2–5 lakh lists customers with ₹2,00,000–₹5,00,000 in the period. Use{" "}
                        <strong className="text-app-fg">0</strong> as the lower bound for “up to” the max only.
                    </p>
                    <button
                        type="button"
                        onClick={handleDownloadBelowThreshold}
                        disabled={exportingBelow}
                        className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-app-card border border-app-gold/50 text-app-gold hover:bg-app-gold-muted disabled:opacity-50"
                    >
                        <Download className="h-4 w-4" />
                        {exportingBelow ? "Downloading…" : "Download CSV"}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <KpiCard title={buyerFocus === "low" ? "In focus (low buyers)" : "Total Customers"} value={kpiTotal.toString()} icon={Users} />
                <KpiCard title="Champions" value={(segCounts["Champions"] || 0).toString()} icon={Crown} />
                <KpiCard title="At Risk" value={(segCounts["At Risk"] || 0).toString()} icon={AlertTriangle} />
                <KpiCard title="Lost" value={(segCounts["Lost"] || 0).toString()} icon={UserX} />
            </div>

            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4">Customer Segments</h3>
                <div className="flex gap-3 flex-wrap">
                    {Object.entries(segCounts).length > 0 ? Object.entries(segCounts).map(([seg, count]) => (
                        <div key={seg} className={`${SEGMENT_COLORS[seg] || 'bg-gray-600'} rounded-lg px-4 py-3 text-center min-w-[120px]`}>
                            <div className="text-2xl font-bold text-app-fg">{count}</div>
                            <div className="text-sm text-app-fg-muted">{seg}</div>
                        </div>
                    )) : <div className="text-app-fg-muted">No segmented customers found in this period.</div>}
                </div>
            </div>

            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4">RFM Customer Map</h3>
                {filteredRfm.length > 0 ? (
                    <ScatterBubbleChart data={filteredRfm} xKey="Recency" yKey="Frequency" zKey="Monetary" nameKey="CUSTOMER_NAME" />
                ) : (
                    <div className="h-40 flex items-center justify-center text-app-fg-muted">
                        {buyerFocus === "low" ? "No low-purchase segments in this period. Try All customers or widen filters." : "No data"}
                    </div>
                )}
            </div>

            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4">RFM Analysis</h3>
                <DataTable
                    data={filteredRfm}
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
                            cell: (item: any) => <span className="text-app-fg font-semibold">{fmt(item.Monetary)}</span>
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

            <div className="bg-app-card border border-app-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-app-fg border-b border-app-border pb-4 mb-4">
                    {buyerFocus === "low" ? "Low purchase customers (revenue, lowest first)" : "Top Customers by Revenue"}
                </h3>
                <DataTable
                    data={displayCustomers}
                    searchable={true}
                    searchPlaceholder="Search customers..."
                    searchKeys={['CUSTOMER_NAME', 'CITY', 'STATE']}
                    pageSizeOptions={[10, 25, 50]}
                    defaultPageSize={10}
                    columns={[
                        {
                            header: '#',
                            accessorKey: '_index',
                            sortable: false,
                            cell: (_, index) => <span className="text-app-fg-muted">{index! + 1}</span> // Fixed index rendering
                        },
                        { header: 'Customer', accessorKey: 'CUSTOMER_NAME', sortable: true },
                        { header: 'City', accessorKey: 'CITY', sortable: true },
                        { header: 'State', accessorKey: 'STATE', sortable: true },
                        {
                            header: 'Revenue',
                            accessorKey: 'Revenue',
                            sortable: true,
                            align: 'right',
                            cell: (item: any) => <span className="text-app-fg font-semibold">{fmt(item.Revenue)}</span>
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
