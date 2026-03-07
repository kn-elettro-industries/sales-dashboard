"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

const FILTER_STORAGE_KEY = "elettro_filter_view";

export interface DateRange {
    from?: Date;
    to?: Date;
}

interface FilterContextType {
    dateRange: DateRange;
    setDateRange: (range: DateRange) => void;
    tenant: string;
    setTenant: (tenant: string) => void;
    selectedStates: string[];
    setSelectedStates: (v: string[]) => void;
    selectedCities: string[];
    setSelectedCities: (v: string[]) => void;
    selectedCustomers: string[];
    setSelectedCustomers: (v: string[]) => void;
    selectedMaterialGroups: string[];
    setSelectedMaterialGroups: (v: string[]) => void;
    selectedFiscalYears: string[];
    setSelectedFiscalYears: (v: string[]) => void;
    selectedMonths: string[];
    setSelectedMonths: (v: string[]) => void;
    saveCurrentView: (name: string) => void;
    loadView: (name: string) => void;
    savedViewNames: string[];
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export function FilterProvider({ children }: { children: ReactNode }) {
    // Always start with empty/default state so server and client first paint match (avoid hydration mismatch)
    const [dateRange, setDateRange] = useState<DateRange>({});
    const [tenant, setTenant] = useState<string>("default_elettro");
    const [selectedStates, setSelectedStates] = useState<string[]>([]);
    const [selectedCities, setSelectedCities] = useState<string[]>([]);
    const [selectedCustomers, setSelectedCustomers] = useState<string[]>([]);
    const [selectedMaterialGroups, setSelectedMaterialGroups] = useState<string[]>([]);
    const [selectedFiscalYears, setSelectedFiscalYears] = useState<string[]>([]);
    const [selectedMonths, setSelectedMonths] = useState<string[]>([]);
    const [savedViewNames, setSavedViewNames] = useState<string[]>([]);
    const [hasHydrated, setHasHydrated] = useState(false);

    // Restore from localStorage only after mount (client-only)
    useEffect(() => {
        try {
            const raw = localStorage.getItem(FILTER_STORAGE_KEY + "_current");
            if (raw) {
                const stored = JSON.parse(raw) as Partial<{ tenant: string; states: string[]; cities: string[]; customers: string[]; materialGroups: string[]; fiscalYears: string[]; months: string[]; dateFrom: string; dateTo: string }>;
                if (stored.tenant) setTenant(stored.tenant);
                if (Array.isArray(stored.states)) setSelectedStates(stored.states);
                if (Array.isArray(stored.cities)) setSelectedCities(stored.cities);
                if (Array.isArray(stored.customers)) setSelectedCustomers(stored.customers);
                if (Array.isArray(stored.materialGroups)) setSelectedMaterialGroups(stored.materialGroups);
                if (Array.isArray(stored.fiscalYears)) setSelectedFiscalYears(stored.fiscalYears);
                if (Array.isArray(stored.months)) setSelectedMonths(stored.months);
                if (stored.dateFrom || stored.dateTo) setDateRange({ from: stored.dateFrom ? new Date(stored.dateFrom) : undefined, to: stored.dateTo ? new Date(stored.dateTo) : undefined });
            }
            const listRaw = localStorage.getItem(FILTER_STORAGE_KEY + "_list");
            if (listRaw) {
                const list = JSON.parse(listRaw) as string[];
                if (Array.isArray(list)) setSavedViewNames(list);
            }
        } catch {
            // ignore
        }
        setHasHydrated(true);
    }, []);

    useEffect(() => {
        if (!hasHydrated || typeof window === "undefined") return;
        const payload = {
            tenant,
            states: selectedStates,
            cities: selectedCities,
            customers: selectedCustomers,
            materialGroups: selectedMaterialGroups,
            fiscalYears: selectedFiscalYears,
            months: selectedMonths,
            dateFrom: dateRange?.from?.toISOString?.()?.slice(0, 10),
            dateTo: dateRange?.to?.toISOString?.()?.slice(0, 10),
        };
        localStorage.setItem(FILTER_STORAGE_KEY + "_current", JSON.stringify(payload));
    }, [hasHydrated, tenant, dateRange, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths]);

    const saveCurrentView = useCallback((name: string) => {
        if (typeof window === "undefined" || !name.trim()) return;
        const payload = { name: name.trim(), tenant, states: selectedStates, cities: selectedCities, customers: selectedCustomers, materialGroups: selectedMaterialGroups, fiscalYears: selectedFiscalYears, months: selectedMonths, dateFrom: dateRange?.from?.toISOString?.()?.slice(0, 10), dateTo: dateRange?.to?.toISOString?.()?.slice(0, 10) };
        const key = FILTER_STORAGE_KEY + "_" + name.trim();
        localStorage.setItem(key, JSON.stringify(payload));
        setSavedViewNames((prev) => {
            const list = prev.includes(name.trim()) ? prev : [...prev, name.trim()];
            localStorage.setItem(FILTER_STORAGE_KEY + "_list", JSON.stringify(list));
            return list;
        });
    }, [tenant, dateRange, selectedStates, selectedCities, selectedCustomers, selectedMaterialGroups, selectedFiscalYears, selectedMonths]);

    const loadView = useCallback((name: string) => {
        if (typeof window === "undefined") return;
        try {
            const raw = localStorage.getItem(FILTER_STORAGE_KEY + "_" + name);
            if (!raw) return;
            const p = JSON.parse(raw);
            setTenant(p.tenant || tenant);
            setSelectedStates(Array.isArray(p.states) ? p.states : []);
            setSelectedCities(Array.isArray(p.cities) ? p.cities : []);
            setSelectedCustomers(Array.isArray(p.customers) ? p.customers : []);
            setSelectedMaterialGroups(Array.isArray(p.materialGroups) ? p.materialGroups : []);
            setSelectedFiscalYears(Array.isArray(p.fiscalYears) ? p.fiscalYears : []);
            setSelectedMonths(Array.isArray(p.months) ? p.months : []);
            setDateRange({ from: p.dateFrom ? new Date(p.dateFrom) : undefined, to: p.dateTo ? new Date(p.dateTo) : undefined });
        } catch {
            // ignore
        }
    }, [tenant]);

    return (
        <FilterContext.Provider value={{
            dateRange, setDateRange,
            tenant, setTenant,
            selectedStates, setSelectedStates,
            selectedCities, setSelectedCities,
            selectedCustomers, setSelectedCustomers,
            selectedMaterialGroups, setSelectedMaterialGroups,
            selectedFiscalYears, setSelectedFiscalYears,
            selectedMonths, setSelectedMonths,
            saveCurrentView,
            loadView,
            savedViewNames,
        }}>
            {children}
        </FilterContext.Provider>
    );
}

export function useFilter() {
    const context = useContext(FilterContext);
    if (context === undefined) {
        throw new Error("useFilter must be used within a FilterProvider");
    }
    return context;
}
