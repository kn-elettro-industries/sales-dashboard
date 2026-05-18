"use client";

import React, { useState, useMemo, useEffect } from 'react';
import { ChevronUp, ChevronDown, Search, ChevronLeft, ChevronRight, Inbox } from 'lucide-react';

export interface ColumnDef<T> {
    header: string;
    accessorKey: keyof T | string;
    sortable?: boolean;
    cell?: (item: T, rowIndex: number) => React.ReactNode;
    align?: 'left' | 'center' | 'right';
    className?: string;
}

interface DataTableProps<T> {
    data: T[];
    columns: ColumnDef<T>[];
    searchable?: boolean;
    searchPlaceholder?: string;
    searchKeys?: (keyof T)[];
    pageSizeOptions?: number[];
    defaultPageSize?: number;
    maxHeight?: string;
    onRowClick?: (item: T) => void;
}

export function DataTable<T extends Record<string, any>>({
    data,
    columns,
    searchable = false,
    searchPlaceholder = "Search...",
    searchKeys,
    pageSizeOptions = [10, 25, 50, 100],
    defaultPageSize = 10,
    maxHeight = "500px",
    onRowClick,
}: DataTableProps<T>) {
    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(defaultPageSize);

    // 1. Filter
    const filteredData = useMemo(() => {
        if (!searchTerm || !searchKeys || searchKeys.length === 0) return data;
        const lower = searchTerm.toLowerCase();
        return data.filter(item =>
            searchKeys.some(key => {
                const val = item[key];
                return val != null && String(val).toLowerCase().includes(lower);
            })
        );
    }, [data, searchTerm, searchKeys]);

    // 2. Sort
    const sortedData = useMemo(() => {
        if (!sortConfig) return filteredData;
        return [...filteredData].sort((a, b) => {
            const av = a[sortConfig.key];
            const bv = b[sortConfig.key];
            if (typeof av === 'string' && typeof bv === 'string')
                return sortConfig.direction === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
            if (av < bv) return sortConfig.direction === 'asc' ? -1 : 1;
            if (av > bv) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });
    }, [filteredData, sortConfig]);

    // 3. Paginate
    const totalPages = Math.max(1, Math.ceil(sortedData.length / pageSize));
    useEffect(() => {
        if (currentPage > totalPages) setCurrentPage(totalPages);
    }, [currentPage, totalPages]);

    const paginatedData = useMemo(() => {
        const start = (currentPage - 1) * pageSize;
        return sortedData.slice(start, start + pageSize);
    }, [sortedData, currentPage, pageSize]);

    const handleSort = (key: string) => {
        setSortConfig(prev =>
            prev?.key === key
                ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
                : { key, direction: 'asc' }
        );
        setCurrentPage(1);
    };

    const alignClass = (align?: 'left' | 'center' | 'right') =>
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left';

    const startEntry = (currentPage - 1) * pageSize + 1;
    const endEntry = Math.min(currentPage * pageSize, sortedData.length);

    return (
        <div className="flex flex-col w-full h-full">

            {/* Controls */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-3">
                {searchable && searchKeys && (
                    <div className="relative w-full sm:w-60">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-app-fg-muted pointer-events-none" />
                        <input
                            type="text"
                            placeholder={searchPlaceholder}
                            value={searchTerm}
                            onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                            className="w-full pl-9 pr-3 py-2 bg-app-bg border border-app-border rounded-lg text-sm text-app-fg placeholder:text-app-fg-muted
                                       focus:outline-none focus:ring-2 focus:ring-app-gold/30 focus:border-app-gold/60 transition-all duration-200"
                        />
                    </div>
                )}
                <div className="flex items-center gap-2 text-xs text-app-fg-muted ml-auto">
                    <span>Show</span>
                    <select
                        value={pageSize}
                        onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                        className="bg-app-bg border border-app-border text-app-fg text-xs rounded-md px-2 py-1.5
                                   focus:outline-none focus:ring-2 focus:ring-app-gold/30 focus:border-app-gold/60 transition-all"
                    >
                        {pageSizeOptions.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <span>rows</span>
                </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto overflow-y-auto border border-app-border rounded-xl" style={{ maxHeight }}>
                <table className="w-full text-sm">
                    <thead className="sticky top-0 z-10">
                        <tr className="bg-app-muted border-b border-app-border">
                            {columns.map((col, i) => (
                                <th
                                    key={i}
                                    className={`py-3 px-4 text-xs font-semibold text-app-fg-muted uppercase tracking-wide select-none
                                        ${alignClass(col.align)} ${col.className || ''}
                                        ${col.sortable !== false ? 'cursor-pointer hover:text-app-fg transition-colors' : ''}`}
                                    onClick={() => col.sortable !== false && handleSort(col.accessorKey as string)}
                                >
                                    <div className={`flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : col.align === 'center' ? 'justify-center' : ''}`}>
                                        <span>{col.header}</span>
                                        {col.sortable !== false && (
                                            <span className="flex flex-col ml-0.5">
                                                <ChevronUp className={`w-3 h-3 -mb-0.5 transition-colors
                                                    ${sortConfig?.key === col.accessorKey && sortConfig.direction === 'asc'
                                                        ? 'text-app-gold' : 'opacity-25'}`} />
                                                <ChevronDown className={`w-3 h-3 -mt-0.5 transition-colors
                                                    ${sortConfig?.key === col.accessorKey && sortConfig.direction === 'desc'
                                                        ? 'text-app-gold' : 'opacity-25'}`} />
                                            </span>
                                        )}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedData.length > 0 ? (
                            paginatedData.map((row, rowIndex) => (
                                <tr
                                    key={rowIndex}
                                    className={`border-b border-app-border/50 transition-colors duration-150
                                        ${rowIndex % 2 === 1 ? 'bg-app-muted/25' : 'bg-app-bg'}
                                        hover:bg-app-hover
                                        ${onRowClick ? 'cursor-pointer' : ''}`}
                                    onClick={() => onRowClick?.(row)}
                                >
                                    {columns.map((col, ci) => {
                                        const absIdx = (currentPage - 1) * pageSize + rowIndex;
                                        return (
                                            <td key={ci} className={`py-3 px-4 ${alignClass(col.align)} ${col.className || ''}`}>
                                                {col.cell ? col.cell(row, absIdx) : (row[col.accessorKey as keyof T] as React.ReactNode)}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={columns.length} className="py-16 bg-app-bg">
                                    <div className="flex flex-col items-center gap-3 text-center">
                                        <div className="h-12 w-12 rounded-full bg-app-muted border border-app-border flex items-center justify-center">
                                            <Inbox className="h-5 w-5 text-app-fg-muted" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-app-fg-muted">No data found</p>
                                            {searchTerm && (
                                                <p className="text-xs text-app-fg-muted mt-1 opacity-70">
                                                    No results for &ldquo;{searchTerm}&rdquo; — try a different term
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {sortedData.length > 0 && (
                <div className="flex flex-col sm:flex-row items-center justify-between mt-3 gap-2">
                    <p className="text-xs text-app-fg-muted">
                        Showing <span className="font-medium text-app-fg">{startEntry}–{endEntry}</span> of{" "}
                        <span className="font-medium text-app-fg">{sortedData.length}</span> entries
                    </p>
                    <div className="flex items-center gap-1.5">
                        <button
                            onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
                            disabled={currentPage === 1}
                            className="h-8 w-8 flex items-center justify-center rounded-md border border-app-border bg-app-bg
                                       text-app-fg-muted hover:border-app-gold/40 hover:text-app-gold
                                       disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </button>

                        <span className="px-3 h-8 flex items-center rounded-md bg-app-gold/10 border border-app-gold/30 text-app-gold text-xs font-semibold tabular-nums">
                            {currentPage} / {totalPages}
                        </span>

                        <button
                            onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
                            disabled={currentPage === totalPages}
                            className="h-8 w-8 flex items-center justify-center rounded-md border border-app-border bg-app-bg
                                       text-app-fg-muted hover:border-app-gold/40 hover:text-app-gold
                                       disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                        >
                            <ChevronRight className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
