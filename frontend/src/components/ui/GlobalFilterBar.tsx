"use client";

import { useState, useEffect, useMemo } from "react";
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
    /** When states are selected, city picklist is limited to cities that appear with those states in data. */
    cities_by_state: Record<string, string[]>;
    customers: string[];
    material_groups: string[];
    fiscal_years: string[];
    months: string[];
    items: string[];
}

function MultiSelect({ label, options, selected, onChange, longLabels = false }: {
    label: string;
    options: string[];
    selected: string[];
    onChange: (v: string[]) => void;
    /** Wider panel + wrap long text (e.g. SKU / item names). */
    longLabels?: boolean;
}) {
    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState("");

    const safeOptions = Array.isArray(options) ? options : [];
    const filtered = safeOptions.filter(o => o.toLowerCase().includes(search.toLowerCase()));

    const summary =
        selected.length === 0
            ? `All ${label}`
            : selected.length === 1 && longLabels
              ? selected[0]
              : `${selected.length} ${label} selected`;

    return (
        <Popover.Root open={isOpen} onOpenChange={setIsOpen}>
            <Popover.Trigger asChild>
                <button
                    type="button"
                    title={longLabels && selected.length > 0 ? selected.join("\n") : undefined}
                    className={`flex w-full items-start justify-between gap-2 bg-app-bg border border-app-border rounded-lg px-3 py-2 hover:border-app-border-strong transition-colors text-sm text-app-fg min-h-[36px] text-left ${
                        longLabels ? "min-w-0" : ""
                    }`}
                >
                    <span className={longLabels ? "break-words whitespace-normal leading-snug min-w-0 flex-1" : "truncate"}>
                        {summary}
                    </span>
                    <ChevronDown className="h-3 w-3 mt-0.5 text-app-fg-muted shrink-0" />
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content
                    className={
                        longLabels
                            ? "bg-app-card border border-app-border rounded-xl shadow-xl min-w-[min(100vw-1rem,28rem)] max-w-[min(100vw-1rem,42rem)] max-h-72 overflow-hidden mt-1 z-50"
                            : "bg-app-card border border-app-border rounded-xl shadow-xl w-64 max-h-72 overflow-hidden mt-1 z-50"
                    }
                    sideOffset={5}
                    align="start"
                >
                    <div className="p-2 border-b border-app-border">
                        <input
                            type="text"
                            placeholder={`Search ${label}...`}
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="w-full bg-app-bg border border-app-border text-app-fg rounded px-2 py-1.5 text-xs outline-none focus:border-app-gold"
                        />
                    </div>
                    {selected.length > 0 && (
                        <button
                            type="button"
                            onClick={() => onChange([])}
                            className="w-full text-left text-xs text-app-gold px-3 py-1.5 hover:bg-app-muted border-b border-app-border"
                        >
                            Clear all
                        </button>
                    )}
                    <div className="overflow-y-auto max-h-48 p-1">
                        {filtered.map(opt => (
                            <label
                                key={opt}
                                className={`flex gap-2 px-2 py-1.5 hover:bg-app-muted rounded cursor-pointer text-sm text-app-fg ${
                                    longLabels ? "items-start" : "items-center"
                                }`}
                            >
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
                                    className="mr-0 mt-1 accent-app-gold shrink-0"
                                />
                                <span
                                    className={
                                        longLabels
                                            ? "break-words whitespace-normal leading-snug min-w-0"
                                            : "truncate"
                                    }
                                >
                                    {opt}
                                </span>
                            </label>
                        ))}
                        {filtered.length === 0 && <div className="text-xs text-app-fg-muted p-2">No results</div>}
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
        selectedItems, setSelectedItems,
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
        states: [], cities: [], cities_by_state: {}, customers: [], material_groups: [], fiscal_years: [], months: [], items: []
    });
    const [exporting, setExporting] = useState(false);

    // Load filter options from backend; items are restricted to selected material groups when any are chosen
    useEffect(() => {
        const params = new URLSearchParams();
        params.set("tenant_id", tenant);
        // Single JSON param so selections survive proxies / URL parsing (repeated keys often break)
        if (selectedMaterialGroups.length > 0) {
            params.set("material_groups_json", JSON.stringify(selectedMaterialGroups));
        }
        fetch(`${API_BASE}/filters/options?${params.toString()}`)
            .then((r) => {
                if (!r.ok) return null;
                return r.json();
            })
            .then((data: FilterOptions | null) => {
                if (data && typeof data === "object" && !("error" in data)) {
                    const cbs = data.cities_by_state;
                    const nextItems = Array.isArray(data.items) ? data.items : [];
                    setOptions({
                        states: Array.isArray(data.states) ? data.states : [],
                        cities: Array.isArray(data.cities) ? data.cities : [],
                        cities_by_state: cbs && typeof cbs === "object" && !Array.isArray(cbs) ? (cbs as Record<string, string[]>) : {},
                        customers: Array.isArray(data.customers) ? data.customers : [],
                        material_groups: Array.isArray(data.material_groups) ? data.material_groups : [],
                        fiscal_years: Array.isArray(data.fiscal_years) ? data.fiscal_years : [],
                        months: Array.isArray(data.months) ? data.months : [],
                        items: nextItems,
                    });
                    setSelectedItems((prev) => {
                        const allowed = new Set(nextItems);
                        const pruned = prev.filter((x) => allowed.has(x));
                        return pruned.length === prev.length ? prev : pruned;
                    });
                }
            })
            .catch(() => {});
    }, [tenant, selectedMaterialGroups, setSelectedItems]);

    const cityOptionsForFilter = useMemo(() => {
        const all = options.cities;
        const byState = options.cities_by_state;
        if (selectedStates.length === 0 || !byState || Object.keys(byState).length === 0) {
            return all;
        }
        const set = new Set<string>();
        for (const s of selectedStates) {
            const list = byState[s];
            if (Array.isArray(list)) {
                list.forEach((c) => set.add(c));
            }
        }
        return Array.from(set).sort((a, b) => a.localeCompare(b));
    }, [options.cities, options.cities_by_state, selectedStates]);

    useEffect(() => {
        if (selectedStates.length === 0) return;
        const allowed = new Set(cityOptionsForFilter);
        const next = selectedCities.filter((c) => allowed.has(c));
        if (next.length !== selectedCities.length) {
            setSelectedCities(next);
        }
    }, [selectedStates, cityOptionsForFilter, selectedCities, setSelectedCities]);

    const activeFilterCount = selectedStates.length + selectedCities.length + selectedCustomers.length + selectedMaterialGroups.length + selectedFiscalYears.length + selectedMonths.length + selectedItems.length;

    const handleExportData = () => {
        try {
            setExporting(true);
            const params = new URLSearchParams();
            params.append("tenant_id", tenant);
            if (dateRange?.from) params.append("start_date", format(dateRange.from, "yyyy-MM-dd"));
            if (dateRange?.to) params.append("end_date", format(dateRange.to, "yyyy-MM-dd"));
            if (selectedStates.length > 0) params.append("states", selectedStates.join(","));
            if (selectedCities.length > 0) params.append("cities", selectedCities.join(","));
            if (selectedCustomers.length > 0) params.append("customers", selectedCustomers.join(","));
            if (selectedMaterialGroups.length > 0) params.append("material_groups", selectedMaterialGroups.join(","));
            if (selectedFiscalYears.length > 0) params.append("fiscal_years", selectedFiscalYears.join(","));
            if (selectedMonths.length > 0) params.append("months", selectedMonths.join(","));
            if (selectedItems.length > 0) params.append("items", selectedItems.join(","));

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
        <div className="bg-app-card border-b border-app-border sticky top-0 z-20 shadow-md">
            {/* Primary Row */}
            <div className="p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
                    <div className="flex items-center gap-2 text-app-fg-muted mr-2 shrink-0">
                        <Filter className="h-4 w-4" />
                        <span className="text-sm font-medium">Filters:</span>
                    </div>

                    {/* Tenant Selector */}
                    <div className="relative shrink-0 flex items-center bg-app-bg border border-app-border rounded-lg px-3 py-1.5 hover:border-app-border-strong transition-colors">
                        <Building2 className="h-4 w-4 text-app-gold mr-2" />
                        <select value={tenant} onChange={(e) => setTenant(e.target.value)}
                            className="bg-transparent text-sm text-app-fg outline-none cursor-pointer pr-4 appearance-none">
                            <option value="default_elettro" className="bg-app-card text-app-fg">All India (Consolidated)</option>
                            <option value="north_region" className="bg-app-card text-app-fg">North Region</option>
                            <option value="south_region" className="bg-app-card text-app-fg">South Region</option>
                        </select>
                    </div>

                    {/* Date Picker */}
                    <Popover.Root open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
                        <Popover.Trigger asChild>
                            <button className="flex shrink-0 items-center bg-app-bg border border-app-border rounded-lg px-3 py-1.5 hover:border-app-border-strong transition-colors text-sm text-app-fg">
                                <CalendarIcon className="h-4 w-4 text-app-gold mr-2" />
                                {dateRange?.from ? (
                                    dateRange.to ? (
                                        <>{format(dateRange.from, "LLL dd, y")} - {format(dateRange.to, "LLL dd, y")}</>
                                    ) : format(dateRange.from, "LLL dd, y")
                                ) : <span>All Time</span>}
                            </button>
                        </Popover.Trigger>
                        <Popover.Portal>
                            <Popover.Content className="bg-app-card border border-app-border rounded-xl shadow-xl w-64 p-2 mt-2 z-50 text-sm" sideOffset={5} align="start">
                                <div className="text-app-fg-muted mb-2 px-2 pt-1 font-medium">Quick Select</div>
                                <div className="grid grid-cols-1 gap-1">
                                    {datePresets.map((preset) => (
                                        <button key={preset.label}
                                            onClick={() => { setDateRange(preset.getRange()); setIsCalendarOpen(false); }}
                                            className="text-left px-3 py-2 hover:bg-app-muted hover:text-app-gold rounded-md transition-colors text-app-fg">
                                            {preset.label}
                                        </button>
                                    ))}
                                </div>
                                <div className="border-t border-app-border my-2"></div>
                                <div className="text-app-fg-muted mb-2 px-2 pt-1 font-medium">Custom Range</div>
                                <div className="px-2 flex flex-col gap-2 pb-2">
                                    <div className="text-xs text-app-fg-muted px-1">Start Date</div>
                                    <input type="date"
                                        className="bg-app-bg border border-app-border text-app-fg rounded p-1.5 text-sm w-full outline-none focus:border-app-gold"
                                        onChange={(e) => setDateRange({ ...dateRange, from: e.target.value ? new Date(e.target.value) : undefined })}
                                        value={dateRange?.from ? format(dateRange.from, "yyyy-MM-dd") : ""}
                                    />
                                    <div className="text-xs text-app-fg-muted px-1 mt-1">End Date</div>
                                    <input type="date"
                                        className="bg-app-bg border border-app-border text-app-fg rounded p-1.5 text-sm w-full outline-none focus:border-app-gold"
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
                            ? 'bg-app-gold/10 text-app-gold border-app-gold/30'
                            : 'bg-app-bg text-app-fg border-app-border hover:border-app-border-strong'
                            }`}>
                        <Filter className="h-3.5 w-3.5 mr-1.5" />
                        Advanced
                        {mounted && activeFilterCount > 0 && (
                            <span className="ml-1.5 bg-app-gold text-app-on-gold text-xs font-bold px-1.5 py-0.5 rounded-full">{activeFilterCount}</span>
                        )}
                    </button>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                    <Popover.Root open={viewsOpen} onOpenChange={setViewsOpen}>
                        <Popover.Trigger asChild>
                            <button className="flex items-center text-sm font-medium border px-3 py-1.5 rounded-lg border-app-border text-app-fg bg-app-muted hover:bg-app-hover">
                                <Bookmark className="h-4 w-4 mr-2" />
                                Views
                                <ChevronDown className="h-3 w-3 ml-1" />
                            </button>
                        </Popover.Trigger>
                        <Popover.Portal>
                            <Popover.Content className="bg-app-card border border-app-border rounded-xl shadow-xl w-56 p-3 mt-2 z-50 text-sm" sideOffset={5} align="end">
                                <div className="font-medium text-app-fg mb-2">Saved views</div>
                                <div className="flex gap-2 mb-2">
                                    <input type="text" placeholder="View name" value={saveViewName} onChange={(e) => setSaveViewName(e.target.value)} className="flex-1 bg-app-bg border border-app-border rounded px-2 py-1 text-app-fg text-xs placeholder:text-app-fg-muted" />
                                    <button type="button" onClick={() => { if (saveViewName.trim()) { saveCurrentView(saveViewName.trim()); setSaveViewName(""); } }} className="px-2 py-1 rounded bg-app-gold text-app-on-gold text-xs font-medium">Save</button>
                                </div>
                                {savedViewNames.length > 0 ? (
                                    <div className="space-y-1 max-h-40 overflow-y-auto">
                                        {savedViewNames.map((name) => (
                                            <button key={name} type="button" onClick={() => { loadView(name); setViewsOpen(false); }} className="w-full flex items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-app-muted text-app-fg">
                                                <FolderOpen className="h-3.5 w-3.5 text-app-gold" />
                                                {name}
                                            </button>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-xs text-app-fg-muted">No saved views yet. Enter a name and click Save.</p>
                                )}
                            </Popover.Content>
                        </Popover.Portal>
                    </Popover.Root>
                    <button
                        onClick={handleExportData}
                        disabled={exporting}
                        className={`flex items-center text-sm font-medium border px-4 py-1.5 rounded-lg transition-colors ${
                            exporting
                                ? "bg-app-border-strong text-app-fg-muted border-app-border cursor-not-allowed"
                                : "text-app-fg bg-app-muted hover:bg-app-hover border-app-border"
                        }`}
                    >
                        <Download className="h-4 w-4 mr-2" />
                        {exporting ? "Preparing CSV..." : "Export Data"}
                    </button>
                </div>
            </div>

            {/* Advanced Filters Row */}
            {showAdvanced && (
                <div className="px-4 pb-4 border-t border-app-border pt-3">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
                        <div className="min-w-0">
                            <label className="text-xs text-app-fg-muted mb-1 block">Fiscal Year (Apr–Mar)</label>
                            <MultiSelect label="FY" options={options.fiscal_years} selected={selectedFiscalYears} onChange={setSelectedFiscalYears} />
                        </div>
                        <div className="min-w-0">
                            <label className="text-xs text-app-fg-muted mb-1 block">Month</label>
                            <MultiSelect label="Months" options={options.months} selected={selectedMonths} onChange={setSelectedMonths} />
                        </div>
                        <div className="min-w-0">
                            <label className="text-xs text-app-fg-muted mb-1 block">State / Region</label>
                            <MultiSelect label="States" options={options.states} selected={selectedStates} onChange={setSelectedStates} />
                        </div>
                        <div className="min-w-0">
                            <label className="text-xs text-app-fg-muted mb-1 block">City {selectedStates.length > 0 ? "(linked to selected states)" : ""}</label>
                            <MultiSelect label="Cities"
                                options={cityOptionsForFilter}
                                selected={selectedCities} onChange={setSelectedCities}
                            />
                        </div>
                        <div className="min-w-0">
                            <label className="text-xs text-app-fg-muted mb-1 block">Customer</label>
                            <MultiSelect label="Customers" options={options.customers} selected={selectedCustomers} onChange={setSelectedCustomers} />
                        </div>
                        <div className="min-w-0">
                            <label className="text-xs text-app-fg-muted mb-1 block">Material Group</label>
                            <MultiSelect label="Groups" options={options.material_groups} selected={selectedMaterialGroups} onChange={setSelectedMaterialGroups} />
                        </div>
                    </div>
                    <div className="mt-3 min-w-0">
                        <label className="text-xs text-app-fg-muted mb-1 block">
                            Item (SKU)
                            {selectedMaterialGroups.length > 0 ? (
                                <span className="text-app-gold"> — only items in selected material group(s)</span>
                            ) : null}
                        </label>
                        <MultiSelect
                            longLabels
                            label="Items"
                            options={options.items}
                            selected={selectedItems}
                            onChange={setSelectedItems}
                        />
                    </div>
                    {activeFilterCount > 0 && (
                        <div className="flex items-center gap-2 mt-3 flex-wrap">
                            {selectedStates.map(s => (
                                <span key={s} className="inline-flex items-center bg-app-muted border border-app-border text-app-fg text-xs px-2 py-1 rounded-full">
                                    {s}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-app-gold" onClick={() => setSelectedStates(selectedStates.filter(x => x !== s))} />
                                </span>
                            ))}
                            {selectedCities.map(c => (
                                <span key={c} className="inline-flex items-center bg-app-muted border border-app-border text-app-fg text-xs px-2 py-1 rounded-full">
                                    {c}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-app-gold" onClick={() => setSelectedCities(selectedCities.filter(x => x !== c))} />
                                </span>
                            ))}
                            {selectedCustomers.map(c => (
                                <span key={c} className="inline-flex items-center bg-app-muted border border-app-border text-app-fg text-xs px-2 py-1 rounded-full">
                                    {c}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-app-gold" onClick={() => setSelectedCustomers(selectedCustomers.filter(x => x !== c))} />
                                </span>
                            ))}
                            {selectedMaterialGroups.map(m => (
                                <span key={m} className="inline-flex items-center bg-app-muted border border-app-border text-app-fg text-xs px-2 py-1 rounded-full">
                                    {m}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-app-gold" onClick={() => setSelectedMaterialGroups(selectedMaterialGroups.filter(x => x !== m))} />
                                </span>
                            ))}
                            {selectedFiscalYears.map(f => (
                                <span key={f} className="inline-flex items-center bg-app-muted border border-app-border text-app-fg text-xs px-2 py-1 rounded-full">
                                    FY: {f}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-app-gold" onClick={() => setSelectedFiscalYears(selectedFiscalYears.filter(x => x !== f))} />
                                </span>
                            ))}
                            {selectedMonths.map(m => (
                                <span key={m} className="inline-flex items-center bg-app-muted border border-app-border text-app-fg text-xs px-2 py-1 rounded-full">
                                    {m}
                                    <X className="h-3 w-3 ml-1 cursor-pointer hover:text-app-gold" onClick={() => setSelectedMonths(selectedMonths.filter(x => x !== m))} />
                                </span>
                            ))}
                            {selectedItems.map(it => (
                                <span
                                    key={it}
                                    title={it}
                                    className="inline-flex items-start gap-1 max-w-full sm:max-w-xl bg-app-muted border border-app-border text-app-fg text-xs px-2 py-1 rounded-lg"
                                >
                                    <span className="break-words whitespace-normal leading-snug min-w-0">
                                        Item: {it}
                                    </span>
                                    <X
                                        className="h-3 w-3 mt-0.5 cursor-pointer shrink-0 hover:text-app-gold"
                                        onClick={() => setSelectedItems(selectedItems.filter(x => x !== it))}
                                    />
                                </span>
                            ))}
                            <button onClick={() => { setSelectedStates([]); setSelectedCities([]); setSelectedCustomers([]); setSelectedMaterialGroups([]); setSelectedFiscalYears([]); setSelectedMonths([]); setSelectedItems([]); }}
                                className="text-xs text-app-gold hover:underline ml-2">
                                Clear all filters
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
