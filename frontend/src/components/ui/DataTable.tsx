"use client";

import React, { useState, useMemo, useEffect } from 'react';
import { ChevronUp, ChevronDown, Search, ChevronLeft, ChevronRight } from 'lucide-react';

export interface ColumnDef<T> {
    header: string;
    accessorKey: keyof T | string; // Using string to allow nested or computed keys if needed, though mostly keyof T
    sortable?: boolean;
    cell?: (item: T, rowIndex: number) => React.ReactNode;
    align?: 'left' | 'center' | 'right';
    className?: string; // Additional classes for the th/td
}

interface DataTableProps<T> {
    data: T[];
    columns: ColumnDef<T>[];
    searchable?: boolean;
    searchPlaceholder?: string;
    searchKeys?: (keyof T)[]; // Which fields to search across
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
    onRowClick
}: DataTableProps<T>) {
    const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(defaultPageSize);

    // 1. Filter
    const filteredData = useMemo(() => {
        if (!searchTerm || !searchKeys || searchKeys.length === 0) return data;
        const lowerSearch = searchTerm.toLowerCase();
        return data.filter(item => {
            return searchKeys.some(key => {
                const val = item[key];
                if (val === null || val === undefined) return false;
                return String(val).toLowerCase().includes(lowerSearch);
            });
        });
    }, [data, searchTerm, searchKeys]);

    // 2. Sort
    const sortedData = useMemo(() => {
        let sortableItems = [...filteredData];
        if (sortConfig !== null) {
            sortableItems.sort((a, b) => {
                const aValue = a[sortConfig.key];
                const bValue = b[sortConfig.key];

                // Handle string comparison
                if (typeof aValue === 'string' && typeof bValue === 'string') {
                    return sortConfig.direction === 'asc'
                        ? aValue.localeCompare(bValue)
                        : bValue.localeCompare(aValue);
                }

                // Handle numeric or other comparison
                if (aValue < bValue) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableItems;
    }, [filteredData, sortConfig]);

    // 3. Paginate
    const totalPages = Math.max(1, Math.ceil(sortedData.length / pageSize));

    useEffect(() => {
        if (currentPage > totalPages && totalPages > 0) {
            setCurrentPage(totalPages);
        }
    }, [currentPage, totalPages]);

    const paginatedData = useMemo(() => {
        const startIndex = (currentPage - 1) * pageSize;
        return sortedData.slice(startIndex, startIndex + pageSize);
    }, [sortedData, currentPage, pageSize]);

    const handleSort = (key: string) => {
        let direction: 'asc' | 'desc' = 'asc';
        if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
        setCurrentPage(1); // Reset to first page on sort
    };

    const getAlignClass = (align?: 'left' | 'center' | 'right') => {
        switch (align) {
            case 'center': return 'text-center';
            case 'right': return 'text-right';
            default: return 'text-left';
        }
    };

    return (
        <div className="flex flex-col w-full h-full">
            {/* Top Controls: Search & Page Size */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
                {searchable && searchKeys && (
                    <div className="relative w-full sm:w-64">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <Search className="h-4 w-4 text-gray-500" />
                        </div>
                        <input
                            type="text"
                            placeholder={searchPlaceholder}
                            value={searchTerm}
                            onChange={(e) => {
                                setSearchTerm(e.target.value);
                                setCurrentPage(1);
                            }}
                            className="block w-full pl-10 pr-3 py-2 border border-[#30363d] rounded-md leading-5 bg-[#0d1117] text-gray-300 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        />
                    </div>
                )}

                <div className="flex items-center space-x-2 text-sm text-gray-400 ml-auto">
                    <span>Show</span>
                    <select
                        value={pageSize}
                        onChange={(e) => {
                            setPageSize(Number(e.target.value));
                            setCurrentPage(1);
                        }}
                        className="bg-[#0d1117] border border-[#30363d] text-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                        {pageSizeOptions.map(size => (
                            <option key={size} value={size}>{size}</option>
                        ))}
                    </select>
                    <span>entries</span>
                </div>
            </div>

            {/* Table Area */}
            <div className="overflow-x-auto overflow-y-auto border border-[#30363d] rounded-lg" style={{ maxHeight }}>
                <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-[#161b22] shadow-[0_1px_0_0_#30363d] z-10">
                        <tr className="text-gray-400">
                            {columns.map((col, i) => (
                                <th
                                    key={i}
                                    className={`py-3 px-4 select-none ${getAlignClass(col.align)} ${col.className || ''} ${col.sortable !== false ? 'cursor-pointer hover:bg-[#2d333b]' : ''}`}
                                    onClick={() => col.sortable !== false && handleSort(col.accessorKey as string)}
                                >
                                    <div className={`flex items-center space-x-1 ${col.align === 'right' ? 'justify-end' : col.align === 'center' ? 'justify-center' : 'justify-start'}`}>
                                        <span>{col.header}</span>
                                        {col.sortable !== false && (
                                            <span className="flex flex-col text-[10px] leading-[0.5] opacity-50">
                                                <ChevronUp className={`w-3 h-3 ${sortConfig?.key === col.accessorKey && sortConfig.direction === 'asc' ? 'text-blue-500 opacity-100' : ''}`} />
                                                <ChevronDown className={`w-3 h-3 -mt-1 ${sortConfig?.key === col.accessorKey && sortConfig.direction === 'desc' ? 'text-blue-500 opacity-100' : ''}`} />
                                            </span>
                                        )}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#30363d]">
                        {paginatedData.length > 0 ? (
                            paginatedData.map((row, rowIndex) => (
                                <tr
                                    key={rowIndex}
                                    className={`bg-[#0d1117] hover:bg-[#21262d] transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
                                    onClick={() => onRowClick && onRowClick(row)}
                                >
                                    {columns.map((col, colIndex) => {
                                        const absoluteIndex = ((currentPage - 1) * pageSize) + rowIndex;
                                        return (
                                            <td key={colIndex} className={`py-3 px-4 ${getAlignClass(col.align)} ${col.className || ''}`}>
                                                {col.cell ? col.cell(row, absoluteIndex) : (row[col.accessorKey as keyof T] as React.ReactNode)}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={columns.length} className="py-8 text-center text-gray-500 bg-[#0d1117]">
                                    No data available
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination Controls */}
            {sortedData.length > 0 && (
                <div className="flex flex-col sm:flex-row items-center justify-between mt-4 text-sm text-gray-400">
                    <div className="mb-4 sm:mb-0">
                        Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length} entries
                    </div>
                    <div className="flex items-center space-x-2">
                        <button
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                            disabled={currentPage === 1}
                            className="p-1 rounded-md border border-[#30363d] bg-[#21262d] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#30363d] transition-colors"
                        >
                            <ChevronLeft className="w-5 h-5" />
                        </button>
                        <div className="flex space-x-1">
                            {/* Simple pagination: show current page and surrounding pages */}
                            <span className="px-3 py-1 bg-blue-600/20 text-blue-400 rounded-md font-medium">
                                {currentPage} / {totalPages}
                            </span>
                        </div>
                        <button
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            disabled={currentPage === totalPages}
                            className="p-1 rounded-md border border-[#30363d] bg-[#21262d] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#30363d] transition-colors"
                        >
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
