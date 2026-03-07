"use client";

import { useState, useEffect } from "react";
import { useFilter } from "../FilterContext";
import { Calendar as CalendarIcon, Filter, Building2, Download, ChevronDown, X, Bookmark, FolderOpen } from "lucide-react";
import { format, subDays, startOfYear } from "date-fns";
import * as Popover from "@radix-ui/react-popover";

import { API_BASE_URL } from "@/lib/api";
const API_BASE = API_BASE_URL;

const datePresets = [
    { label: "All Time", getRange: () => ({ from: undefined, to: undefined }) },
    { label: "Last 7 Days", getRange: () => ({ from: subDays(new Date(), 7), to: new Date() }) },
    { label: "Last 30 Days", getRange: () => ({ from: subDays(new Date(), 30), to: new Date() }) },
    { label: "Last 90 Days", getRange: () => ({ from: subDays(new Date(), 90), to: new Date() }) },
    { label: "Year to Date", getRange: () => ({ from: startOfYear(new Date()), to: new Date() }) },
];

interface FilterOptions {
    states: string[];
    cities: string[];
    customers: string[];
    material_groups: string[];
    fiscal_years: string[];
    months: string[];
}

function MultiSelect({ label, options, selected, onChange }: {
    label: string; options: string[]; selected: string[]; onChange: (v: string[]) => void;
}) {
    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState("");

    const filtered = options.filter(o => o.toLowerCase().includes(search.toLowerCase()));

    return (
        <Popover.Root open={isOpen} onOpenChange={setIsOpen}>
            <Popover.Trigger asChild>
                <button className="flex items-center justify-between w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 hover:border-gray-500 transition-colors text-sm text-gray-200 min-h-[36px]">
                    <span className="truncate">
                        {selected.length === 0 ? `All ${label}` : `${selected.length} ${label} selected`}
                    </span>
                    <ChevronDown className="h-3 w-3 ml-2 text-gray-400 shrink-0" />
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content
                    className="bg-[#161b22] border border-[#30363d] rounded-xl shadow-xl w-64 max-h-72 overflow-hidden mt-1 z-50"
                    sideOffset={5} align="start"
                >
                    <div className="p-2 border-b border-[#30363d]">
                        <input
                            type="text" placeholder={`Search ${label}...`} value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="w-full bg-[#0d1117] border border-[#30363d] text-gray-200 rounded px-2 py-1.5 text-xs outline-none focus:border-[#daa520]"
                        />
                    </div>
                    {selected.length > 0 && (
                        <button onClick={() => onChange([])}
                            className="w-full text-left text-xs text-[#daa520] px-3 py-1.5 hover:bg-[#2d333b] border-b border-[#30363d]">
                            Clear all
                        </button>
                    )}
                    <div className="overflow-y-auto max-h-48 p-1">
                        {filtered.map(opt => (
                            <label key={opt} className="flex items-center px-2 py-1.5 hover:bg-[#2d333b] rounded cursor-pointer text-sm text-gray-300">
                                <input
                                    type="checkbox"
                                    checked={selected.includes(opt)}
                                    onChange={() => {
                                        onChange(
                                            selected.includes(opt)
                                                ? selected.filter(s => s !== opt)
                                                : [...selected, opt]
                                        );
                                    }}
                                    className="mr-2 accent-[#daa520]"
                                />
                                <span className="truncate">{opt}</span>
                            </label>
                        ))}
                        {filtered.length === 0 && <div className="text-xs text-gray-500 p-2">No results</div>}
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

export default function GlobalFilterBar() {
    const {
        dateRange, setDateRange, tenant, setTenant,
        selectedStates, setSelectedStates,
        selectedCities, setSelectedCities,
        selectedCustomers, setSelectedCustomers,
        selectedMaterialGroups, setSelectedMaterialGroups,
        selectedFiscalYears, setSelectedFiscalYears,
        selectedMonths, setSelectedMonths,
        saveCurrentView,
        loadView,
        savedViewNames,
    } = useFilter();

    const [isCalendarOpen, setIsCalendarOpen] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [viewsOpen, setViewsOpen] = useState(false);
    const [saveViewName, setSaveViewName] = useState("");
    const [mounted, setMounted] = useState(false);
    useEffect(() => setMounted(true), []);
    const [options, setOptions] = useState<FilterOptions>({
        states: [], cities: [], customers: [], material_groups: [], fiscal_years: [], months: []
    });
    const [exporting, setExporting] = useState(false);

    // Load filter options from backend
    useEffect(() => {
        fetch(`${API_BASE}/filters/options?tenant_id=${tenant}`)
            .then(r => r.json())
            .then(setOptions)
            .catch(() => { });
    }, [tenant]);

    const activeFilterCount = selectedStates.length + selectedCities.length + selectedCustomers.length + selectedMaterialGroups.length + selectedFiscalYears.length + selectedMonths.length;

    const handleExportData = () => {
        try {
            setExporting(true);
            const params = new URLSearchParams();
            params.append("tenant_id", tenant);
            if (dateRange?.from) params.append("start_date", dateRange.from.toISOString());
            if (dateRange?.to) params.append("end_date", dateRange.to.toISOString());
            if (selectedStates.length > 0) params.append("states", selectedStates.join(","));
            if (selectedCities.length > 0) params.append("cities", selectedCities.join(","));
            if (selectedCustomers.length > 0) params.append("customers", selectedCustomers.join(","));
            if (selectedMaterialGroups.length > 0) params.append("material_groups", selectedMaterialGroups.join(","));
            if (selectedFiscalYears.length > 0) params.append("fiscal_years", selectedFiscalYears.join(","));
            if (selectedMonths.length > 0) params.append("months", selectedMonths.join(","));

            const url = `${API_BASE}/export/data?${params.toString()}`;
            const a = document.createElement("a");
            a.style.display = "none";
            a.href = url;
            a.setAttribute("download", "");
            a.target = "_self";
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                setExporting(false);
            }, 150);
        } catch {
            setExporting(false);
        }
    };

    return (
        <div className="bg-[#161b22] border-b border-[#30363d] sticky top-0 z-20 shadow-md">
            {/* Primary Row */}
            <div className="p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
                    <div className="flex items-center gap-2 text-gray-400 mr-2 shrink-0">
                        <Filter className="h-4 w-4" />
                        <span className="text-sm font-medium">Filters:</span>
                    </div>

                    {/* Tenant Selector */}
                    <div className="relative shrink-0 flex items-center bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-1.5 hover:border-gray-500 transition-colors">
                        <Building2 className="h-4 w-4 text-[#daa520] mr-2" />
                        <select value={tenant} onChange={(e) => setTenant(e.target.value)}
                            className="bg-transparent text-sm text-gray-200 outline-none cursor-pointer pr-4 appearance-none">
                            <option value="default_elettro" className="bg-[#0d1117] text-white">All India (Consolidated)</option>
                            <option value="north_region" className="bg-[#0d1117] text-white">North Region</option>
                            <option value="south_region" className="bg-[#0d1117] text-white">South Region</option>
                        </select>
                    </div>

                    {/* Date Picker */}
                    <Popover.Root open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
                        <Popover.Trigger asChild>
                            <button className="flex shrink-0 items-center bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-1.5 hover:border-gray-500 transition-colors text-sm text-gray-200">
                                <CalendarIcon className="h-4 w-4 text-[#daa520] mr-2" />
                                {dateRange?.from ? (
                                    dateRange.to ? (
                                        <>{format(dateRange.from, "LLL dd, y")} - {format(dateRange.to, "LLL dd, y")}</>
                                    ) : format(dateRange.from, "LLL dd, y")
                                ) : <span>All Time</span>}
                            </button>
                        </Popover.Trigger>
                        <Popover.Portal>
                            <Popover.Content className="bg-[#161b22] border border-[#30363d] rounded-xl shadow-xl w-64 p-2 mt-2 z-50 text-sm" sideOffset={5} align="start">
                                <div className="text-gray-400 mb-2 px-2 pt-1 font-medium">Quick Select</div>
                                <div className="grid grid-cols-1 gap-1">
                                    {datePresets.map((preset) => (
                                        <button key={preset.label}
                                            onClick={() => { setDateRange(preset.getRange()); setIsCalendarOpen(false); }}
                                            className="text-left px-3 py-2 hover:bg-[#2d333b] hover:text-[#daa520] rounded-md transition-colors text-gray-300">
                                            {preset.label}
                                        </button>
                                    ))}
                                </div>
                                <div className="border-t border-[#30363d] my-2"></div>
                                <div className="text-gray-400 mb-2 px-2 pt-1 font-medium">Custom Range</div>
                                <div className="px-2 flex flex-col gap-2 pb-2">
                                    <div className="text-xs text-gray-500 px-1">Start Date</div>
                                    <input type="date"
                                        className="bg-[#0d1117] border border-[#30363d] text-gray-200 rounded p-1.5 text-sm w-full outline-none focus:border-[#daa520]"
                                        onChange={(e) => setDateRange({ ...dateRange, from: e.target.value ? new Date(e.target.value) : undefined })}
                                        value={dateRange?.from ? format(dateRange.from, "yyyy-MM-dd") : ""}
                                    />
                                    <div className="text-xs text-gray-500 px-1 mt-1">End Date</div>
                                    <input type="date"
                                        className="bg-[#0d1117] border border-[#30363d] text-gray-200 rounded p-1.5 text-sm w-full outline-none focus:border-[#daa520]"
                                        onChange={(e) => setDateRange({ ...dateRange, to: e.target.value ? new Date(e.target.value) : undefined })}
                                        value={dateRange?.to ? format(dateRange.to, "yyyy-MM-dd") : ""}
                                    />
                                </div>
                            </Popover.Content>
                        </Popover.Portal>
                    </Popover.Root>

                    {/* Advanced Filters Toggle - badge only after mount to avoid hydration mismatch */}
                    <button onClick={() => setShowAdvanced(!showAdvanced)}
                        className={`flex items-center shrink-0 text-sm font-medium px-3 py-1.5 rounded-lg border transition-colors ${showAdvanced || (mounted && activeFilterCount > 0)
                            ? 'bg-[#daa520]/10 text-[#daa520] border-[#daa520]/30'
                            : 'bg-[#0d1117] text-gray-300 border-[#30363d] hover:border-gray-500'
                            }`}>
                        <Filter className="h-3.5 w-3.5 mr-1.5" />
                        Advanced
                        {mounted && activeFilterCount > 0 && (
                            <span className="ml-1.5 bg-[#daa520] text-black text-xs font-bold px-1.5 py-0.5 rounded-full">{activeFilterCount}</span>
                        )}
                    </button>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                    <Popover.Root open={viewsOpen} onOpenChange={setViewsOpen}>
                        <Popover.Trigger asChild>
                            <button className="flex items-center text-sm font-medium border px-3 py-1.5 rounded-lg border-[#30363d] text-gray-300 bg-[#2d333b] hover:bg-[#3d444d]">
                                <Bookmark className="h-4 w-4 mr-2" />
                                Views
                                <ChevronDown className="h-3 w-3 ml-1" />
                            </button>
                        </Popover.Trigger>
                        <Popover.Portal>
                            <Popover.Content className="bg-[#161b22] border border-[#30363d] rounded-xl shadow-xl w-56 p-3 mt-2 z-50 text-sm" sideOffset={5} align="end">
                                <div className="font-medium text-gray-300 mb-2">Saved views</div>
                                <div className="flex gap-2 mb-2">
                                    <input type="text" placeholder="View name" value={saveViewName} onChange={(e) => setSaveViewName(e.target.value)} className="flex-1 bg-[#0d1117] border border-[#30363d] rounded px-2 py-1 text-white text-xs" />
                                    <button type="button" onClick={() => { if (saveViewName.trim()) { saveCurrentView(saveViewName.trim()); setSaveViewName(""); } }} className="px-2 py-1 rounded bg-[#daa520] text-[#0d1117] text-xs font-medium">Save</button>
                                </div>
                                {savedViewNames.length > 0 ? (
                                    <div className="space-y-1 max-h-40 overflow-y-auto">
                                        {savedViewNames.map((name) => (
                                            <button key={name} type="button" onClick={() => { loadView(name); setViewsOpen(false); }} className="w-full flex items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-[#2d333b] text-gray-300">
                                                <FolderOpen className="h-3.5 w-3.5 text-[#daa520]" />
                                                {name}
                                            </button>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-xs text-gray-500">No saved views yet. Enter a name and click Save.</p>
                                )}
                            </Popover.Content>
                        </Popover.Portal>
                    </Popover.Root>
                    <button
                        onClick={handleExportData}
                        disabled={exporting}
                        className={`flex items-center text-sm font-medium border px-4 py-1.5 rounded-lg transition-colors ${
                            exporting
                                ? "bg-[#30363d] text-gray-400 border-[#30363d] cursor-not-allowed"
                                : "text-gray-300 bg-[#2d333b] hover:bg-[#3d444d] border-[#30363d]"
                        }`}
                    >
                        <Download className="h-4 w-4 mr-2" />
                        {exporting ? "Preparing CSV..." : "Export Data"}
                    </button>
                </div>
            </div>

            {/* Advanced Filters Row */}
            {showAdvanced && (
                <div className="px-4 pb-4 border-t border-[#30363d] pt-3">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                        <div>
                            <label className="text-xs text-gray-500 mb-1 block">Fiscal Year</label>
                            <MultiSelect label="FY" options={options.fiscal_years} selected={selectedFiscalYears} onChange={setSelectedFiscalYears} />
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 mb-1 block">Month</label>
                            <MultiSelect label="Months" options={options.months} selected={selectedMonths} onChange={setSelectedMonths} />
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 mb-1 block">State / Region</label>
                            <MultiSelect label="States" options={options.states} selected={selectedStates} onChange={setSelectedStates} />
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 mb-1 block">City</label>
                            <MultiSelect label="Cities"
                                options={options.cities}
                                selected={selectedCities} onChange={setSelectedCities}
                            />
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 mb-1 block">Customer</label>
                            <MultiSelect label="Customers" options={options.customers} selected={selectedCustomers} onChange={setSelectedCustomers} />
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 mb-1 block">Material Group</label>
                            <MultiSelect label="Groups" options={options.material_groups} selected={selectedMaterialGroups} onChange={setSelectedMaterialGroups} />
                        </div>
                    </div>
                    {activeFilterCount > 0 && (
                        <div className="flex items-center gap-2 mt-3 flex-wrap">
                            {selectedStates.map(s => (
                                <span key={s} className="inline-flex items-center bg-[#2d333b] text-gray-300 text-xs px-2 py-1 rounded-full">
                                    {s}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-[#daa520]" onClick={() => setSelectedStates(selectedStates.filter(x => x !== s))} />
                                </span>
                            ))}
                            {selectedCities.map(c => (
                                <span key={c} className="inline-flex items-center bg-[#2d333b] text-gray-300 text-xs px-2 py-1 rounded-full">
                                    {c}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-[#daa520]" onClick={() => setSelectedCities(selectedCities.filter(x => x !== c))} />
                                </span>
                            ))}
                            {selectedCustomers.map(c => (
                                <span key={c} className="inline-flex items-center bg-[#2d333b] text-gray-300 text-xs px-2 py-1 rounded-full">
                                    {c}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-[#daa520]" onClick={() => setSelectedCustomers(selectedCustomers.filter(x => x !== c))} />
                                </span>
                            ))}
                            {selectedMaterialGroups.map(m => (
                                <span key={m} className="inline-flex items-center bg-[#2d333b] text-gray-300 text-xs px-2 py-1 rounded-full">
                                    {m}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-[#daa520]" onClick={() => setSelectedMaterialGroups(selectedMaterialGroups.filter(x => x !== m))} />
                                </span>
                            ))}
                            {selectedFiscalYears.map(f => (
                                <span key={f} className="inline-flex items-center bg-[#2d333b] text-gray-300 text-xs px-2 py-1 rounded-full">
                                    FY: {f}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-[#daa520]" onClick={() => setSelectedFiscalYears(selectedFiscalYears.filter(x => x !== f))} />
                                </span>
                            ))}
                            {selectedMonths.map(m => (
                                <span key={m} className="inline-flex items-center bg-[#2d333b] text-gray-300 text-xs px-2 py-1 rounded-full">
                                    {m}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-[#daa520]" onClick={() => setSelectedMonths(selectedMonths.filter(x => x !== m))} />
                                </span>
                            ))}
                            <button onClick={() => { setSelectedStates([]); setSelectedCities([]); setSelectedCustomers([]); setSelectedMaterialGroups([]); setSelectedFiscalYears([]); setSelectedMonths([]); }}
                                className="text-xs text-[#daa520] hover:underline ml-2">
                                Clear all filters
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
