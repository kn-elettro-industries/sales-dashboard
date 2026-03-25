"use client";

import React, { useState, useEffect } from "react";
import { format } from "date-fns";
import { Download, FileText, ChevronDown, Loader2, Filter, LayoutDashboard, FileBarChart, DollarSign, ShoppingCart, Users, TrendingUp } from "lucide-react";
import { useFilter } from "@/components/FilterContext";
import { fetchAllCustomers, fetchStateData, fetchMonthlySales, fetchKpiSummary, fetchMaterialPerformance, fetchItemDetails, API_BASE_URL } from "@/lib/api";
import { KpiCard } from "@/components/ui/KpiCard";
import { DataTable } from "@/components/ui/DataTable";
import { formatAmount, formatCr } from "@/lib/format";

const REPORT_TYPES = [
    { id: "Executive Summary", label: "Executive Summary (All Data)", icon: FileText, needsEntity: false },
    { id: "Distributor Strategy Report", label: "Distributor Strategy Report", icon: FileText, needsEntity: true },
    { id: "State Wise", label: "State/Region Deep Dive", icon: FileText, needsEntity: true },
    { id: "Material Group Wise", label: "Material Category Deep Dive", icon: FileText, needsEntity: true },
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

export default function ReportsPage() {
    const { tenant, dateRange, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths } = useFilter();

    // Tab state
    const [activeTab, setActiveTab] = useState<'interactive' | 'export'>('interactive');

    // Export State
    const [downloading, setDownloading] = useState(false);
    const [selectedReport, setSelectedReport] = useState("Executive Summary");
    const [selectedEntity, setSelectedEntity] = useState("All");
    const [filterCustomer, setFilterCustomer] = useState("All");
    const [filterState, setFilterState] = useState("All");
    const [filterMaterial, setFilterMaterial] = useState("All");
    const [entityOptions, setEntityOptions] = useState<string[]>([]);
    const [customerOptions, setCustomerOptions] = useState<string[]>([]);
    const [stateOptions, setStateOptions] = useState<string[]>([]);
    const [isLoadingOptions, setIsLoadingOptions] = useState(false);

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

    // Load Interactive Data
    useEffect(() => {
        if (activeTab !== 'interactive') return;

        const loadDocs = async () => {
            setIsLoadingInteractive(true);
            try {
                const params = {
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

                const [kpis, mats, items] = await Promise.all([
                    fetchKpiSummary(params),
                    fetchMaterialPerformance(params),
                    fetchItemDetails(params)
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
    }, [activeTab, tenant, dateRange, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths]);

    // Fetch dynamic options based on selected report type
    useEffect(() => {
        if (activeTab !== 'export') return;

        const loadOptions = async () => {
            const report = REPORT_TYPES.find(r => r.id === selectedReport);
            if (!report?.needsEntity) {
                setEntityOptions([]);
                setSelectedEntity("All");
                return;
            }

            setIsLoadingOptions(true);
            try {
                if (selectedReport === "Distributor Strategy Report") {
                    if (customerOptions.length > 0) {
                        setEntityOptions(customerOptions);
                    } else {
                        const data = await fetchAllCustomers({ tenant });
                        setEntityOptions(data.map((c: any) => c.CUSTOMER_NAME).filter(Boolean).sort());
                    }
                } else if (selectedReport === "State Wise") {
                    if (stateOptions.length > 0) {
                        setEntityOptions(stateOptions);
                    } else {
                        const data = await fetchStateData({ tenant });
                        setEntityOptions(data.map((s: any) => s.STATE).filter(Boolean).sort());
                    }
                } else if (selectedReport === "Material Group Wise") {
                    setEntityOptions(["AIR FILTER", "SELF LOCKING PA 66 CABLE TIE", "JUNCTION BOXES", "POLYMIDE FLEXIBLE CONDUIT & SLITTED", "POLYAMIDE CONDUIT GLAND"]);
                }
            } catch (e) {
                console.error("Failed to fetch entity options", e);
            } finally {
                setIsLoadingOptions(false);
                setSelectedEntity("All");
            }
        };

        loadOptions();
    }, [activeTab, selectedReport, customerOptions, stateOptions, tenant]);

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

    // Keep report-level filters in sync with global filters so user doesn't have to re-select
    useEffect(() => {
        // If exactly one customer selected globally, default isolate + entity to that
        if (selectedCustomers.length === 1) {
            if (filterCustomer === "All") {
                setFilterCustomer(selectedCustomers[0]);
            }
            if (selectedReport === "Distributor Strategy Report" && selectedEntity === "All") {
                setSelectedEntity(selectedCustomers[0]);
            }
        }
        // If exactly one state selected globally
        if (selectedStates.length === 1) {
            if (filterState === "All") {
                setFilterState(selectedStates[0]);
            }
            if (selectedReport === "State Wise" && selectedEntity === "All") {
                setSelectedEntity(selectedStates[0]);
            }
        }
        // If exactly one material group selected globally
        if (selectedMaterialGroups.length === 1) {
            if (filterMaterial === "All") {
                setFilterMaterial(selectedMaterialGroups[0]);
            }
            if (selectedReport === "Material Group Wise" && selectedEntity === "All") {
                setSelectedEntity(selectedMaterialGroups[0]);
            }
        }
    }, [
        selectedCustomers,
        selectedStates,
        selectedMaterialGroups,
        selectedReport,
        filterCustomer,
        filterState,
        filterMaterial,
        selectedEntity,
    ]);

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const queryParams = new URLSearchParams({
                tenant_id: tenant,
                report_type: selectedReport,
            });

            if (selectedEntity && selectedEntity !== "All") {
                queryParams.append("specific_entity", selectedEntity);
            }
            if (filterCustomer !== "All") queryParams.append("filter_customer", filterCustomer);
            if (filterState !== "All") queryParams.append("filter_state", filterState);
            if (filterMaterial !== "All") queryParams.append("filter_material", filterMaterial);

            if (selectedStates.length > 0) queryParams.append("states", selectedStates.join(','));
            if (selectedCities.length > 0) queryParams.append("cities", selectedCities.join(','));
            if (selectedCustomers.length > 0) queryParams.append("customers", selectedCustomers.join(','));
            if (selectedMaterialGroups.length > 0) queryParams.append("material_groups", selectedMaterialGroups.join(','));
            if (selectedFiscalYears.length > 0) queryParams.append("fiscal_years", selectedFiscalYears.join(','));
            if (selectedMonths.length > 0) queryParams.append("months", selectedMonths.join(','));

            if (dateRange?.from) queryParams.append("start_date", format(dateRange.from, "yyyy-MM-dd"));
            if (dateRange?.to) queryParams.append("end_date", format(dateRange.to, "yyyy-MM-dd"));

            const url = `${API_BASE_URL}/reports/download?${queryParams.toString()}`;

            const res = await fetch(url, { cache: "no-store" });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: "Report generation failed." }));
                alert(err?.detail || "No data for the selected filters. Widen filters or choose a different period.");
                return;
            }
            const blob = await res.blob();
            const disposition = res.headers.get("Content-Disposition");
            const filename = disposition?.match(/filename="?([^";]+)"?/)?.[1] || "ELETTRO_Report.pdf";
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
            const filename = disposition?.match(/filename=\"?([^\";]+)\"?/)?.[1] || "ELETTRO_Dynamic_Report.pdf";
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

    return (
        <div className="space-y-6 max-w-7xl mx-auto">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-2xl font-bold text-white">Executive Sales Reports</h2>
                    <p className="text-gray-400 mt-1">
                        Strategy-grade PDF packs and interactive views that always respect your global filters.
                    </p>
                </div>
            </div>

            {/* Custom Tabs */}
            <div className="flex space-x-1 bg-[#161b22] border border-[#30363d] p-1 rounded-lg w-fit">
                <button
                    onClick={() => setActiveTab('interactive')}
                    className={`flex items-center px-4 py-2 rounded-md transition-all text-sm font-medium ${activeTab === 'interactive'
                        ? 'bg-[#daa520] text-[#0d1117] shadow-sm'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-[#21262d]'
                        }`}
                >
                    <LayoutDashboard size={16} className="mr-2" />
                    Interactive Reports
                </button>
                <button
                    onClick={() => setActiveTab('export')}
                    className={`flex items-center px-4 py-2 rounded-md transition-all text-sm font-medium ${activeTab === 'export'
                        ? 'bg-[#daa520] text-[#0d1117] shadow-sm'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-[#21262d]'
                        }`}
                >
                    <FileBarChart size={16} className="mr-2" />
                    Export PDF Report
                </button>
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
                        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 md:p-6">
                            <h3 className="text-[#daa520] font-medium mb-4 flex items-center">
                                <FileBarChart size={18} className="mr-2" />
                                Material Group Breakdown
                            </h3>
                            {isLoadingInteractive ? (
                                <div className="h-64 flex items-center justify-center">
                                    <Loader2 className="w-8 h-8 animate-spin text-[#daa520]" />
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

                        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 md:p-6">
                            <h3 className="text-[#daa520] font-medium mb-4 flex items-center">
                                <LayoutDashboard size={18} className="mr-2" />
                                Item Level Detail
                            </h3>
                            {isLoadingInteractive ? (
                                <div className="h-64 flex items-center justify-center">
                                    <Loader2 className="w-8 h-8 animate-spin text-[#daa520]" />
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
                    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 md:p-8">
                        {/* Top row: step titles align on one baseline (desktop) */}
                        <div className="hidden lg:grid lg:grid-cols-2 lg:gap-8 lg:mb-3">
                            <span className="text-sm font-medium text-gray-300 leading-5">1. Select Report Type</span>
                            <span className="text-sm font-medium text-gray-300 leading-5">2. Select Target Entity</span>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 lg:gap-8 gap-8 items-start">
                            {/* Column 1 — report types */}
                            <div className="flex flex-col gap-3 min-w-0">
                                <label className="lg:hidden text-sm font-medium text-gray-300 leading-5">1. Select Report Type</label>
                                <div className="grid gap-3">
                                    {REPORT_TYPES.map((report) => (
                                        <button
                                            key={report.id}
                                            type="button"
                                            onClick={() => setSelectedReport(report.id)}
                                            className={`flex items-center p-4 rounded-lg border transition-all text-left min-h-[3.25rem] ${selectedReport === report.id
                                                ? 'bg-[#2a2414] border-[#daa520] text-[#daa520]'
                                                : 'bg-[#0d1117] border-[#30363d] text-gray-400 hover:border-gray-500 hover:text-gray-200'
                                                }`}
                                        >
                                            <report.icon size={20} className="mr-3 flex-shrink-0" />
                                            <span className="font-medium">{report.label}</span>
                                        </button>
                                    ))}
                                </div>

                                <div className="mt-4 rounded-lg border border-[#30363d]/90 bg-[#0d1117]/40 overflow-hidden">
                                    <button
                                        type="button"
                                        onClick={() => setAdvancedExportOpen((o) => !o)}
                                        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left text-sm text-gray-400 hover:text-gray-200 hover:bg-[#161b22]/80 transition-colors"
                                        aria-expanded={advancedExportOpen}
                                    >
                                        <span>
                                            <span className="text-gray-500 block text-xs font-normal mb-0.5">Optional</span>
                                            <span className="font-medium text-gray-300">Dynamic cross-filter PDF</span>
                                            <span className="block text-xs text-gray-600 mt-1 font-normal">Breakdown + top-N — only if you need it.</span>
                                        </span>
                                        <ChevronDown
                                            className={`w-5 h-5 text-gray-500 shrink-0 transition-transform ${advancedExportOpen ? "rotate-180" : ""}`}
                                        />
                                    </button>
                                    {advancedExportOpen && (
                                        <div className="border-t border-[#30363d] px-3 py-4 space-y-4 bg-[#0d1117]">
                                            <p className="text-xs text-gray-500 flex items-start gap-2">
                                                <Filter size={14} className="mt-0.5 shrink-0 text-[#daa520]/80" />
                                                Uses your current global filters. Choose primary/secondary dimensions and top-N.
                                            </p>
                                            <div className="grid grid-cols-1 gap-4">
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-xs text-gray-500">Primary Breakdown</span>
                                                    <select
                                                        value={dynPrimary}
                                                        onChange={(e) => {
                                                            const next = e.target.value;
                                                            setDynPrimary(next);
                                                            if (dynSecondary === next) setDynSecondary("");
                                                        }}
                                                        className="w-full min-h-[2.75rem] bg-[#0d1117] text-white border border-[#30363d] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#daa520]"
                                                    >
                                                        {DYNAMIC_DIMENSIONS.map((d) => (
                                                            <option key={d.id} value={d.id}>
                                                                {d.label}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-xs text-gray-500">Secondary Breakdown (optional)</span>
                                                    <select
                                                        value={dynSecondary}
                                                        onChange={(e) => setDynSecondary(e.target.value)}
                                                        className="w-full min-h-[2.75rem] bg-[#0d1117] text-white border border-[#30363d] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#daa520]"
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
                                                        <span className="text-xs text-gray-500">Top N (3–50)</span>
                                                        <input
                                                            type="number"
                                                            min={3}
                                                            max={50}
                                                            value={dynTopN}
                                                            onChange={(e) => setDynTopN(Number(e.target.value))}
                                                            className="w-full min-h-[2.75rem] bg-[#0d1117] text-white border border-[#30363d] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#daa520]"
                                                        />
                                                    </div>
                                                    <label className="flex items-center gap-2 text-sm text-gray-300 select-none pb-1">
                                                        <input
                                                            type="checkbox"
                                                            checked={dynIncludePivot}
                                                            onChange={(e) => setDynIncludePivot(e.target.checked)}
                                                            disabled={!dynSecondary}
                                                            className="accent-[#daa520] shrink-0"
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
                                                            ? "bg-[#30363d] text-gray-400 cursor-not-allowed border-[#30363d]"
                                                            : "bg-[#161b22] text-[#daa520] border-[#daa520]/40 hover:border-[#daa520] hover:bg-[#2a2414]"
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
                            </div>

                            {/* Column 2 — entity + main download */}
                            <div className="flex flex-col gap-6 min-w-0">
                                <div>
                                    <label className="lg:hidden text-sm font-medium text-gray-300 leading-5 mb-2 block">2. Select Target Entity</label>

                                    {REPORT_TYPES.find(r => r.id === selectedReport)?.needsEntity ? (
                                        <div className="flex flex-col gap-3">
                                            <select
                                                value={selectedEntity}
                                                onChange={(e) => setSelectedEntity(e.target.value)}
                                                disabled={isLoadingOptions || entityOptions.length === 0}
                                                className="w-full bg-[#0d1117] text-white border border-[#30363d] rounded-lg px-3 py-3 outline-none focus:border-[#daa520] disabled:opacity-50 min-h-[3rem]"
                                            >
                                                <option value="All">Summary (All {selectedReport.split(' ')[0]}s)</option>
                                                {entityOptions.map(opt => (
                                                    <option key={opt} value={opt}>{opt}</option>
                                                ))}
                                            </select>

                                            {isLoadingOptions && (
                                                <p className="text-sm text-[#daa520] flex items-center gap-2">
                                                    <Loader2 size={14} className="animate-spin shrink-0" />
                                                    Loading options...
                                                </p>
                                            )}
                                            {selectedEntity !== "All" && (
                                                <div className="bg-[#2a2414] border border-[#daa520]/20 text-[#daa520] p-3 rounded-lg text-sm flex items-start gap-2 w-full">
                                                    <Filter size={16} className="mt-0.5 shrink-0" />
                                                    <p>This report will be <b>exclusively filtered</b> for {selectedEntity}, rendering a 4-page deep dive.</p>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-6 text-center text-gray-500 text-sm leading-relaxed">
                                            <p>The Executive Summary includes all data by default.</p>
                                            <p className="mt-1">No specific entity required.</p>
                                        </div>
                                    )}
                                </div>

                                <div className="border-t border-[#30363d] pt-6 space-y-3">
                                    <p className="text-xs text-gray-500">
                                        Respects <b className="text-gray-400">global filters</b> (date range, state, customer, material, etc.).
                                    </p>
                                    <button
                                        type="button"
                                        onClick={handleDownload}
                                        disabled={downloading}
                                        className={`w-full py-4 rounded-lg font-bold text-lg flex items-center justify-center gap-3 transition-all shadow-lg
                                            ${downloading
                                                ? 'bg-[#30363d] text-gray-400 cursor-not-allowed shadow-none'
                                                : 'bg-gradient-to-r from-[#b8860b] to-[#daa520] text-[#0d1117] hover:scale-[1.01] hover:shadow-[#daa520]/20'
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
                                    <p className="text-xs text-gray-500 text-center">Large reports may take 15–30 seconds.</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="mt-8 bg-[#0d1117] border border-[#30363d] rounded-xl p-6 flex items-start">
                        <div className="bg-[#161b22] p-3 rounded-lg mr-4 border border-[#30363d]">
                            <FileText className="text-gray-400 w-6 h-6" />
                        </div>
                        <div>
                            <h4 className="text-white font-medium mb-1">Looking for deeply customized reports?</h4>
                            <p className="text-sm text-gray-400 leading-relaxed max-w-3xl">
                                The native Next.js reporting engine directly connects to FastAPI to render real-time insights based on your global filter context. Customizing the report logic requires modifying the backend generator.
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
