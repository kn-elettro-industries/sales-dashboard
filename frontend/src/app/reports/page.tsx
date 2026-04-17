"use client";

import React, { useState, useEffect, useMemo } from "react";
import { format } from "date-fns";
import { Download, FileText, ChevronDown, Loader2, Filter, LayoutDashboard, FileBarChart, DollarSign, ShoppingCart, Users, TrendingUp, GitCompare, ArrowLeftRight } from "lucide-react";
import { useFilter } from "@/components/FilterContext";
import { fetchAllCustomers, fetchStateData, fetchKpiSummary, fetchMaterialPerformance, fetchItemDetails, fetchFyComparison, fetchDashboardSummary, type FyComparisonRow, API_BASE_URL } from "@/lib/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { DataTable } from "@/components/ui/DataTable";
import { formatAmount, formatCr } from "@/lib/format";

const REPORT_TYPES = [
    { id: "Executive Summary", label: "Executive Summary (All Data)", icon: FileText },
    { id: "Distributor Strategy Report", label: "Distributor Strategy Report", icon: FileText },
    { id: "State Wise", label: "State/Region Deep Dive", icon: FileText },
    { id: "Material Group Wise", label: "Material Category Deep Dive", icon: FileText },
];

const DYNAMIC_DIMENSIONS = [
    { id: "customer", label: "Customer" },
    { id: "state", label: "State" },
    { id: "city", label: "City" },
    { id: "material_group", label: "Material Group" },
    { id: "item", label: "Item" },
    { id: "month", label: "Month" },
    { id: "fiscal_year", label: "Fiscal Year" },
];

type PeriodComparison = {
    revenue_pct: number;
    orders_pct: number;
    customers_pct: number;
    average_order_value_pct: number;
};

export default function ReportsPage() {
    const { tenant, dateRange, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths, selectedItems } = useFilter();

    // Tab state
    const [activeTab, setActiveTab] = useState<'interactive' | 'export'>('interactive');

    // Export State
    const [downloading, setDownloading] = useState(false);
    const [selectedReport, setSelectedReport] = useState("Executive Summary");
    /** Distributor Strategy PDF: include branded cover (default on). */
    const [distributorIncludeCover, setDistributorIncludeCover] = useState(true);
    const [filterCustomer, setFilterCustomer] = useState("All");
    const [filterState, setFilterState] = useState("All");
    const [filterMaterial, setFilterMaterial] = useState("All");
    const [customerOptions, setCustomerOptions] = useState<string[]>([]);
    const [stateOptions, setStateOptions] = useState<string[]>([]);

    // Dynamic (Streamlit-like) builder state
    const [dynPrimary, setDynPrimary] = useState("customer");
    const [dynSecondary, setDynSecondary] = useState<string>("");
    const [dynTopN, setDynTopN] = useState<number>(12);
    const [dynIncludePivot, setDynIncludePivot] = useState<boolean>(false);
    const [dynDownloading, setDynDownloading] = useState(false);
    /** Advanced cross-filter PDF — tucked away; rarely used */
    const [advancedExportOpen, setAdvancedExportOpen] = useState(false);

    // Interactive State
    const [kpiData, setKpiData] = useState<any>(null);
    const [materialData, setMaterialData] = useState<any[]>([]);
    const [itemData, setItemData] = useState<any[]>([]);
    const [isLoadingInteractive, setIsLoadingInteractive] = useState(false);
    const [fyComparisonRows, setFyComparisonRows] = useState<FyComparisonRow[]>([]);
    const [fyComparisonMessage, setFyComparisonMessage] = useState<string | undefined>(undefined);
    const [isLoadingFyComparison, setIsLoadingFyComparison] = useState(false);
    const [periodComparison, setPeriodComparison] = useState<PeriodComparison | null>(null);
    const [loadingPeriodComparison, setLoadingPeriodComparison] = useState(false);

    const baseReportParams = useMemo(
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

    // FY comparison (all report tabs): ignores global FY filter so multiple FYs appear in range
    useEffect(() => {
        let cancelled = false;
        (async () => {
            setIsLoadingFyComparison(true);
            try {
                const res = await fetchFyComparison(baseReportParams);
                if (!cancelled) {
                    setFyComparisonRows(res.rows);
                    setFyComparisonMessage(res.message);
                }
            } catch {
                if (!cancelled) {
                    setFyComparisonRows([]);
                    setFyComparisonMessage(undefined);
                }
            } finally {
                if (!cancelled) setIsLoadingFyComparison(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [baseReportParams]);

    // vs previous period (same-length window) — same logic as Executive Summary dashboard
    useEffect(() => {
        let cancelled = false;
        (async () => {
            setLoadingPeriodComparison(true);
            try {
                const res = await fetchDashboardSummary(baseReportParams);
                if (cancelled) return;
                const msg = res?.message ? String(res.message) : "";
                if (msg.toLowerCase().includes("backend error")) {
                    setPeriodComparison(null);
                    return;
                }
                setPeriodComparison(res?.comparison ?? null);
            } catch {
                if (!cancelled) setPeriodComparison(null);
            } finally {
                if (!cancelled) setLoadingPeriodComparison(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [baseReportParams]);

    // Load Interactive Data
    useEffect(() => {
        if (activeTab !== 'interactive') return;

        const loadDocs = async () => {
            setIsLoadingInteractive(true);
            try {
                const [kpis, mats, items] = await Promise.all([
                    fetchKpiSummary(baseReportParams),
                    fetchMaterialPerformance(baseReportParams),
                    fetchItemDetails(baseReportParams),
                ]);

                setKpiData(kpis);
                setMaterialData(mats || []);
                setItemData(items || []);
            } catch (e) {
                console.error("Failed to load interactive report data", e);
            } finally {
                setIsLoadingInteractive(false);
            }
        };

        loadDocs();
    }, [activeTab, baseReportParams]);

    // Load Advanced Options once
    useEffect(() => {
        const loadAdvanced = async () => {
            try {
                const dataCust = await fetchAllCustomers({ tenant });
                setCustomerOptions(dataCust.map((c: any) => c.CUSTOMER_NAME).filter(Boolean).sort());

                const dataState = await fetchStateData({ tenant });
                setStateOptions(dataState.map((s: any) => s.STATE).filter(Boolean).sort());

            } catch (e) {
                console.error("Failed to fetch advanced context", e);
            }
        };
        loadAdvanced();
    }, [tenant]);

    // Keep report-level filter dropdowns in sync with global filters (not used for single-entity PDF scope anymore)
    useEffect(() => {
        if (selectedCustomers.length === 1 && filterCustomer === "All") {
            setFilterCustomer(selectedCustomers[0]);
        }
        if (selectedStates.length === 1 && filterState === "All") {
            setFilterState(selectedStates[0]);
        }
        if (selectedMaterialGroups.length === 1 && filterMaterial === "All") {
            setFilterMaterial(selectedMaterialGroups[0]);
        }
    }, [
        selectedCustomers,
        selectedStates,
        selectedMaterialGroups,
        filterCustomer,
        filterState,
        filterMaterial,
    ]);

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const queryParams = new URLSearchParams({
                tenant_id: tenant,
                report_type: selectedReport,
            });

            if (filterCustomer !== "All") queryParams.append("filter_customer", filterCustomer);
            if (filterState !== "All") queryParams.append("filter_state", filterState);
            if (filterMaterial !== "All") queryParams.append("filter_material", filterMaterial);

            if (selectedStates.length > 0) queryParams.append("states", selectedStates.join(','));
            if (selectedCities.length > 0) queryParams.append("cities", selectedCities.join(','));
            if (selectedCustomers.length > 0) queryParams.append("customers", selectedCustomers.join(','));
            if (selectedMaterialGroups.length > 0) queryParams.append("material_groups", selectedMaterialGroups.join(','));
            if (selectedFiscalYears.length > 0) queryParams.append("fiscal_years", selectedFiscalYears.join(','));
            if (selectedMonths.length > 0) queryParams.append("months", selectedMonths.join(','));
            if (selectedItems.length > 0) queryParams.append("items", selectedItems.join(','));

            if (dateRange?.from) queryParams.append("start_date", format(dateRange.from, "yyyy-MM-dd"));
            if (dateRange?.to) queryParams.append("end_date", format(dateRange.to, "yyyy-MM-dd"));

            if (selectedReport === "Distributor Strategy Report") {
                queryParams.append("include_cover", distributorIncludeCover ? "true" : "false");
            }

            const url = `${API_BASE_URL}/reports/download?${queryParams.toString()}`;

            const res = await fetch(url, { cache: "no-store" });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: "Report generation failed." }));
                alert(err?.detail || "No data for the selected filters. Widen filters or choose a different period.");
                return;
            }
            const blob = await res.blob();
            const disposition = res.headers.get("Content-Disposition");
            const filename = disposition?.match(/filename="?([^";]+)"?/)?.[1] || "KN_Elettro_Intelligence_Report.pdf";
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            a.style.display = "none";
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(a.href);
            document.body.removeChild(a);
        } catch (error) {
            console.error("Error triggering download:", error);
            alert("Network error triggering download.");
        } finally {
            setDownloading(false);
        }
    };

    const handleDynamicDownload = async () => {
        setDynDownloading(true);
        try {
            const payload = {
                tenant_id: tenant,
                start_date: dateRange?.from ? format(dateRange.from, "yyyy-MM-dd") : undefined,
                end_date: dateRange?.to ? format(dateRange.to, "yyyy-MM-dd") : undefined,
                states: selectedStates.length > 0 ? selectedStates.join(",") : undefined,
                cities: selectedCities.length > 0 ? selectedCities.join(",") : undefined,
                customers: selectedCustomers.length > 0 ? selectedCustomers.join(",") : undefined,
                material_groups: selectedMaterialGroups.length > 0 ? selectedMaterialGroups.join(",") : undefined,
                fiscal_years: selectedFiscalYears.length > 0 ? selectedFiscalYears.join(",") : undefined,
                months: selectedMonths.length > 0 ? selectedMonths.join(",") : undefined,
                items: selectedItems.length > 0 ? selectedItems.join(",") : undefined,
                spec: {
                    title: "Cross-Filter Report",
                    primary_dimension: dynPrimary,
                    secondary_dimension: dynSecondary ? dynSecondary : null,
                    top_n: Math.max(3, Math.min(50, Number(dynTopN) || 12)),
                    include_trend: true,
                    include_share: true,
                    include_top_table: true,
                    include_pivot: dynIncludePivot && !!dynSecondary && dynSecondary !== dynPrimary,
                }
            };

            const res = await fetch(`${API_BASE_URL}/reports/dynamic`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: "Dynamic report generation failed." }));
                alert(err?.detail || "Dynamic report generation failed.");
                return;
            }

            const blob = await res.blob();
            const disposition = res.headers.get("Content-Disposition");
            const filename = disposition?.match(/filename=\"?([^\";]+)\"?/)?.[1] || "KN_Elettro_Intelligence_Dynamic_Report.pdf";
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            a.style.display = "none";
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(a.href);
            document.body.removeChild(a);
        } catch (error) {
            console.error("Error generating dynamic report:", error);
            alert("Network error generating dynamic report.");
        } finally {
            setDynDownloading(false);
        }
    };

    // Formatting (platform units: Cr / L / K)
    const fmtCr = formatCr;
    const fmt = formatAmount;

    const exportDownloadSection = (
        <div className="border-t border-app-border pt-6 space-y-3">
            <p className="text-xs text-app-fg-muted">
                Respects <b className="text-app-fg">global filters</b> (date range, state, customer, material, etc.).
            </p>
            <button
                type="button"
                onClick={handleDownload}
                disabled={downloading}
                className={`w-full py-4 rounded-lg font-bold text-lg flex items-center justify-center gap-3 transition-all shadow-lg
                    ${downloading
                        ? "bg-app-border-strong text-app-fg-muted cursor-not-allowed shadow-none"
                        : "bg-gradient-to-r from-app-gold-hover to-app-gold text-app-on-gold hover:scale-[1.01] hover:shadow-lg hover:ring-1 hover:ring-app-gold/30"
                    }
                `}
            >
                {downloading ? (
                    <>
                        <Loader2 className="w-5 h-5 animate-spin shrink-0" />
                        Generating Dynamic PDF...
                    </>
                ) : (
                    <>
                        <Download className="w-5 h-5 shrink-0" />
                        Download Industrial Report
                    </>
                )}
            </button>
            <p className="text-xs text-app-fg-muted text-center">Large reports may take 15–30 seconds.</p>
        </div>
    );

    return (
        <div className="space-y-6 max-w-7xl mx-auto">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-2xl font-bold text-app-fg">Executive Sales Reports</h2>
                    <p className="text-app-fg-muted mt-1">
                        Strategy-grade PDF packs and interactive views that always respect your global filters.
                    </p>
                </div>
            </div>

            {/* Custom Tabs */}
            <div className="flex space-x-1 bg-app-card border border-app-border p-1 rounded-lg w-fit">
                <button
                    onClick={() => setActiveTab('interactive')}
                    className={`flex items-center px-4 py-2 rounded-md transition-all text-sm font-medium ${activeTab === 'interactive'
                        ? 'bg-app-gold text-app-on-gold shadow-sm'
                        : 'text-app-fg-muted hover:text-app-fg hover:bg-app-hover'
                        }`}
                >
                    <LayoutDashboard size={16} className="mr-2" />
                    Interactive Reports
                </button>
                <button
                    onClick={() => setActiveTab('export')}
                    className={`flex items-center px-4 py-2 rounded-md transition-all text-sm font-medium ${activeTab === 'export'
                        ? 'bg-app-gold text-app-on-gold shadow-sm'
                        : 'text-app-fg-muted hover:text-app-fg hover:bg-app-hover'
                        }`}
                >
                    <FileBarChart size={16} className="mr-2" />
                    Export PDF Report
                </button>
            </div>

            {/* YoY + period analysis: visible on both Interactive and Export tabs */}
            <div className="bg-app-card border-2 border-app-gold/35 rounded-xl p-4 md:p-6 shadow-lg shadow-black/20">
                <h3 className="text-lg text-app-gold font-semibold mb-1 flex items-center gap-2 flex-wrap">
                    <GitCompare size={22} className="shrink-0" />
                    YoY &amp; period comparison
                </h3>
                <p className="text-xs text-app-fg-muted mb-4 max-w-4xl">
                    <strong className="text-app-fg">Period</strong> compares your selected date range to the <strong className="text-app-fg">immediately preceding period</strong> of the same length (needs start + end dates).
                    <strong className="text-app-fg"> Fiscal years</strong> below ignore the global FY filter so multiple FYs can appear; <strong className="text-app-fg">YoY revenue</strong> compares each FY to the prior FY in the table (needs two or more FY rows).
                </p>

                {/* vs previous calendar period */}
                <div className="mb-6">
                    <h4 className="text-sm font-medium text-app-fg mb-2 flex items-center gap-2">
                        <ArrowLeftRight size={16} className="text-app-gold" />
                        Selected period vs previous period
                    </h4>
                    {loadingPeriodComparison ? (
                        <div className="h-16 flex items-center justify-center rounded-lg border border-app-border/50 bg-app-bg/30">
                            <Loader2 className="w-6 h-6 animate-spin text-app-gold" />
                        </div>
                    ) : periodComparison ? (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {(
                                [
                                    ["Revenue", periodComparison.revenue_pct],
                                    ["Orders", periodComparison.orders_pct],
                                    ["Customers", periodComparison.customers_pct],
                                    ["Avg order value", periodComparison.average_order_value_pct],
                                ] as const
                            ).map(([label, pct]) => (
                                <div
                                    key={label}
                                    className="rounded-lg border border-app-border bg-app-bg px-3 py-2 text-center"
                                >
                                    <div className="text-[10px] uppercase tracking-wide text-app-fg-muted">{label}</div>
                                    <div
                                        className={`text-lg font-semibold ${
                                            pct >= 0 ? "text-emerald-400" : "text-red-400"
                                        }`}
                                    >
                                        {pct > 0 ? "+" : ""}
                                        {pct}%
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-app-fg-muted rounded-lg border border-dashed border-app-border bg-app-bg/40 px-3 py-3">
                            Set a <strong className="text-app-fg">start and end date</strong> in the global filter bar (top of the page) to see percentage change vs the previous period of equal length.
                        </p>
                    )}
                </div>

                <h4 className="text-sm font-medium text-app-fg mb-2 flex items-center gap-2">
                    <TrendingUp size={16} className="text-app-gold" />
                    Fiscal year breakdown &amp; YoY
                </h4>
                {isLoadingFyComparison ? (
                    <div className="h-40 flex items-center justify-center rounded-lg border border-app-border/50 bg-app-bg/30">
                        <Loader2 className="w-8 h-8 animate-spin text-app-gold" />
                    </div>
                ) : fyComparisonMessage && fyComparisonRows.length === 0 ? (
                    <p className="text-sm text-app-fg-muted">{fyComparisonMessage}</p>
                ) : fyComparisonRows.length === 0 ? (
                    <p className="text-sm text-app-fg-muted">
                        No fiscal-year rows for the current filters. Try <strong className="text-app-fg">All Time</strong> or a wider date range, or check that uploaded data includes dates.
                    </p>
                ) : (
                    <DataTable<FyComparisonRow>
                        columns={[
                            { header: "Fiscal Year", accessorKey: "fiscal_year" },
                            {
                                header: "Revenue",
                                accessorKey: "revenue",
                                align: "right",
                                cell: (item) => <span className="text-app-fg font-medium">{fmtCr(item.revenue)}</span>,
                            },
                            { header: "Orders", accessorKey: "orders", align: "right" },
                            { header: "Customers", accessorKey: "customers", align: "right" },
                            {
                                header: "Avg order",
                                accessorKey: "avg_order_value",
                                align: "right",
                                cell: (item) => fmt(item.avg_order_value),
                            },
                            {
                                header: "YoY revenue",
                                accessorKey: "revenue_yoy_pct",
                                align: "right",
                                cell: (item) =>
                                    item.revenue_yoy_pct == null ? (
                                        <span className="text-app-fg-muted">—</span>
                                    ) : (
                                        <span
                                            className={
                                                item.revenue_yoy_pct >= 0 ? "text-emerald-400" : "text-red-400"
                                            }
                                        >
                                            {item.revenue_yoy_pct > 0 ? "+" : ""}
                                            {item.revenue_yoy_pct}%
                                        </span>
                                    ),
                            },
                        ]}
                        data={fyComparisonRows}
                        defaultPageSize={12}
                    />
                )}
            </div>

            {activeTab === 'interactive' && (
                <div className="space-y-6 animate-in fade-in duration-300">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <KpiCard title="Filtered Revenue" value={kpiData ? fmtCr(kpiData.revenue) : "0"} icon={DollarSign} />
                        <KpiCard title="Total Orders" value={kpiData ? kpiData.orders?.toLocaleString() : "0"} icon={ShoppingCart} />
                        <KpiCard title="Active Customers" value={kpiData ? kpiData.customers?.toLocaleString() : "0"} icon={Users} />
                        <KpiCard title="Avg Order Value" value={kpiData ? fmt(kpiData.revenue / Math.max(kpiData.orders, 1)) : "0"} icon={TrendingUp} />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-app-card border border-app-border rounded-xl p-4 md:p-6">
                            <h3 className="text-app-gold font-medium mb-4 flex items-center">
                                <FileBarChart size={18} className="mr-2" />
                                Material Group Breakdown
                            </h3>
                            {isLoadingInteractive ? (
                                <div className="h-64 flex items-center justify-center">
                                    <Loader2 className="w-8 h-8 animate-spin text-app-gold" />
                                </div>
                            ) : (
                                <DataTable
                                    columns={[
                                        { header: "Material Group", accessorKey: "ITEM_NAME_GROUP" },
                                        { header: "Revenue", accessorKey: "Revenue", cell: (item) => fmt(item["Revenue"]) },
                                        { header: "Orders", accessorKey: "Orders" },
                                        { header: "Share %", accessorKey: "Share", cell: (item) => `${item["Share"]}%` },
                                    ]}
                                    data={materialData}
                                    defaultPageSize={10}
                                />
                            )}
                        </div>

                        <div className="bg-app-card border border-app-border rounded-xl p-4 md:p-6">
                            <h3 className="text-app-gold font-medium mb-4 flex items-center">
                                <LayoutDashboard size={18} className="mr-2" />
                                Item Level Detail
                            </h3>
                            {isLoadingInteractive ? (
                                <div className="h-64 flex items-center justify-center">
                                    <Loader2 className="w-8 h-8 animate-spin text-app-gold" />
                                </div>
                            ) : (
                                <DataTable
                                    columns={[
                                        { header: "Item Code/Name", accessorKey: "Item" },
                                        { header: "Category", accessorKey: "Category" },
                                        { header: "Revenue", accessorKey: "Revenue", cell: (item) => fmt(item["Revenue"]) },
                                        { header: "Qty", accessorKey: "Quantity", cell: (item) => Math.round(item["Quantity"]).toLocaleString() },
                                    ]}
                                    data={itemData}
                                    defaultPageSize={10}
                                />
                            )}
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'export' && (
                <div className="animate-in fade-in duration-300">
                    <div className="bg-app-card border border-app-border rounded-xl p-6 md:p-8">
                        <div className="hidden lg:block mb-3">
                            <span className="text-sm font-medium text-app-fg leading-5">Select Report Type</span>
                        </div>

                        <div className="grid grid-cols-1 gap-8 items-start">
                            <div className="flex flex-col gap-3 min-w-0">
                                <label className="lg:hidden text-sm font-medium text-app-fg leading-5">Select Report Type</label>
                                <div className="grid gap-3">
                                    {REPORT_TYPES.map((report) => (
                                        <button
                                            key={report.id}
                                            type="button"
                                            onClick={() => setSelectedReport(report.id)}
                                            className={`flex items-center p-4 rounded-lg border transition-all text-left min-h-[3.25rem] ${selectedReport === report.id
                                                ? 'bg-app-gold-muted border-app-gold text-app-gold'
                                                : 'bg-app-bg border-app-border text-app-fg-muted hover:border-app-border-strong hover:text-app-fg'
                                                }`}
                                        >
                                            <report.icon size={20} className="mr-3 flex-shrink-0" />
                                            <span className="font-medium">{report.label}</span>
                                        </button>
                                    ))}
                                </div>

                                {selectedReport === "Distributor Strategy Report" && (
                                    <label className="flex items-start gap-3 rounded-lg border border-app-border bg-app-bg/60 px-4 py-3 text-sm text-app-fg cursor-pointer select-none">
                                        <input
                                            type="checkbox"
                                            checked={distributorIncludeCover}
                                            onChange={(e) => setDistributorIncludeCover(e.target.checked)}
                                            className="accent-app-gold mt-0.5 shrink-0"
                                        />
                                        <span>
                                            <span className="font-medium text-app-fg">Include cover page</span>
                                            <span className="block text-xs text-app-fg-muted mt-1">
                                                Uncheck to start the PDF directly on the performance summary (no branded title page).
                                            </span>
                                        </span>
                                    </label>
                                )}

                                <div className="mt-4 rounded-lg border border-app-border/90 bg-app-bg/40 overflow-hidden">
                                    <button
                                        type="button"
                                        onClick={() => setAdvancedExportOpen((o) => !o)}
                                        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left text-sm text-app-fg-muted hover:text-app-fg hover:bg-app-card/80 transition-colors"
                                        aria-expanded={advancedExportOpen}
                                    >
                                        <span>
                                            <span className="text-app-fg-muted block text-xs font-normal mb-0.5">Optional</span>
                                            <span className="font-medium text-app-fg">Dynamic cross-filter PDF</span>
                                            <span className="block text-xs text-app-fg-muted mt-1 font-normal">Breakdown + top-N — only if you need it.</span>
                                        </span>
                                        <ChevronDown
                                            className={`w-5 h-5 text-app-fg-muted shrink-0 transition-transform ${advancedExportOpen ? "rotate-180" : ""}`}
                                        />
                                    </button>
                                    {advancedExportOpen && (
                                        <div className="border-t border-app-border px-3 py-4 space-y-4 bg-app-bg">
                                            <p className="text-xs text-app-fg-muted flex items-start gap-2">
                                                <Filter size={14} className="mt-0.5 shrink-0 text-app-gold/80" />
                                                Uses your current global filters. Choose primary/secondary dimensions and top-N.
                                            </p>
                                            <div className="grid grid-cols-1 gap-4">
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-xs text-app-fg-muted">Primary Breakdown</span>
                                                    <select
                                                        value={dynPrimary}
                                                        onChange={(e) => {
                                                            const next = e.target.value;
                                                            setDynPrimary(next);
                                                            if (dynSecondary === next) setDynSecondary("");
                                                        }}
                                                        className="w-full min-h-[2.75rem] bg-app-bg text-app-fg border border-app-border rounded-lg px-3 py-2 text-sm outline-none focus:border-app-gold placeholder:text-app-fg-muted"
                                                    >
                                                        {DYNAMIC_DIMENSIONS.map((d) => (
                                                            <option key={d.id} value={d.id}>
                                                                {d.label}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-xs text-app-fg-muted">Secondary Breakdown (optional)</span>
                                                    <select
                                                        value={dynSecondary}
                                                        onChange={(e) => setDynSecondary(e.target.value)}
                                                        className="w-full min-h-[2.75rem] bg-app-bg text-app-fg border border-app-border rounded-lg px-3 py-2 text-sm outline-none focus:border-app-gold placeholder:text-app-fg-muted"
                                                    >
                                                        <option value="">None</option>
                                                        {DYNAMIC_DIMENSIONS.filter((d) => d.id !== dynPrimary).map((d) => (
                                                            <option key={d.id} value={d.id}>
                                                                {d.label}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
                                                    <div className="flex flex-col gap-1">
                                                        <span className="text-xs text-app-fg-muted">Top N (3–50)</span>
                                                        <input
                                                            type="number"
                                                            min={3}
                                                            max={50}
                                                            value={dynTopN}
                                                            onChange={(e) => setDynTopN(Number(e.target.value))}
                                                            className="w-full min-h-[2.75rem] bg-app-bg text-app-fg border border-app-border rounded-lg px-3 py-2 text-sm outline-none focus:border-app-gold placeholder:text-app-fg-muted"
                                                        />
                                                    </div>
                                                    <label className="flex items-center gap-2 text-sm text-app-fg select-none pb-1">
                                                        <input
                                                            type="checkbox"
                                                            checked={dynIncludePivot}
                                                            onChange={(e) => setDynIncludePivot(e.target.checked)}
                                                            disabled={!dynSecondary}
                                                            className="accent-app-gold shrink-0"
                                                        />
                                                        Include Pivot Table
                                                    </label>
                                                </div>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={handleDynamicDownload}
                                                disabled={dynDownloading}
                                                className={`w-full py-3 rounded-lg font-bold text-base flex items-center justify-center gap-3 transition-all border
                                                    ${
                                                        dynDownloading
                                                            ? "bg-app-border-strong text-app-fg-muted cursor-not-allowed border-app-border"
                                                            : "bg-app-card text-app-gold border-app-gold/40 hover:border-app-gold hover:bg-app-gold-muted"
                                                    }
                                                `}
                                            >
                                                {dynDownloading ? (
                                                    <>
                                                        <Loader2 className="w-5 h-5 animate-spin shrink-0" />
                                                        Generating Dynamic Report...
                                                    </>
                                                ) : (
                                                    <>
                                                        <Download className="w-5 h-5 shrink-0" />
                                                        Download Dynamic Report (Cross-Filter)
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {exportDownloadSection}
                            </div>
                        </div>
                    </div>

                    <div className="mt-8 bg-app-bg border border-app-border rounded-xl p-6 flex items-start">
                        <div className="bg-app-card p-3 rounded-lg mr-4 border border-app-border">
                            <FileText className="text-app-fg-muted w-6 h-6" />
                        </div>
                        <div>
                            <h4 className="text-app-fg font-medium mb-1">Looking for deeply customized reports?</h4>
                            <p className="text-sm text-app-fg-muted leading-relaxed max-w-3xl">
                                The native Next.js reporting engine directly connects to FastAPI to render real-time insights based on your global filter context. Customizing the report logic requires modifying the backend generator.
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
