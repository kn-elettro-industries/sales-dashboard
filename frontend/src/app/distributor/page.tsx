"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useFilter } from "@/components/FilterContext";
import { DataTable } from "@/components/ui/DataTable";
import {
    fetchAllCustomers,
    fetchSalesTargets,
    saveDistributorTarget,
    fetchDistributorVsTarget,
    downloadDistributorVsTargetPdf,
    API_BASE_URL,
} from "@/lib/api";
import { formatAmount } from "@/lib/format";
import { Loader2, Target, AlertCircle, Download } from "lucide-react";

function currentYearMonth(): string {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function DistributorVsTargetPage() {
    const { tenant } = useFilter();
    const [yearMonth, setYearMonth] = useState(currentYearMonth);
    const [customerOptions, setCustomerOptions] = useState<string[]>([]);
    const [customer, setCustomer] = useState("");
    const [pctOfCompany, setPctOfCompany] = useState("");
    const [absoluteTarget, setAbsoluteTarget] = useState("");
    const [companyGoal, setCompanyGoal] = useState<number | null>(null);
    const [saving, setSaving] = useState(false);
    const [loadingReport, setLoadingReport] = useState(false);
    const [report, setReport] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [saveMsg, setSaveMsg] = useState<string | null>(null);
    const [pdfLoading, setPdfLoading] = useState(false);

    const fmt = formatAmount;

    useEffect(() => {
        (async () => {
            try {
                const rows = await fetchAllCustomers({ tenant });
                const names = (rows || []).map((r: any) => r.CUSTOMER_NAME).filter(Boolean).sort() as string[];
                setCustomerOptions(names);
            } catch {
                setCustomerOptions([]);
            }
        })();
    }, [tenant]);

    useEffect(() => {
        (async () => {
            try {
                const t = await fetchSalesTargets(tenant);
                setCompanyGoal(t?.target_revenue ?? null);
            } catch {
                setCompanyGoal(null);
            }
        })();
    }, [tenant]);

    const impliedFromPct = useMemo(() => {
        const p = parseFloat(pctOfCompany.replace(",", "."));
        if (Number.isNaN(p) || companyGoal == null || companyGoal <= 0) return null;
        return (companyGoal * p) / 100;
    }, [pctOfCompany, companyGoal]);

    const handleSaveTarget = async () => {
        if (!customer.trim()) {
            setError("Select a distributor (customer).");
            return;
        }
        setError(null);
        setSaveMsg(null);
        setSaving(true);
        try {
            const abs = absoluteTarget.trim();
            const hasAbs = abs !== "";
            const hasPct = pctOfCompany.trim() !== "";
            if (hasAbs && hasPct) {
                setError("Use either ₹ target OR % of company goal — clear one.");
                return;
            }
            if (!hasAbs && !hasPct) {
                setError("Enter a ₹ target or a % of company goal.");
                return;
            }
            if (hasPct) {
                const p = parseFloat(pctOfCompany.replace(",", "."));
                if (Number.isNaN(p) || p < 0 || p > 100) {
                    setError("Percent must be between 0 and 100.");
                    return;
                }
                await saveDistributorTarget({
                    tenant_id: tenant,
                    customer_name: customer.trim(),
                    year_month: yearMonth,
                    allocation_pct_of_company_goal: p,
                });
            } else {
                const v = Number(abs.replace(/,/g, ""));
                if (Number.isNaN(v) || v < 0) {
                    setError("Invalid ₹ amount.");
                    return;
                }
                await saveDistributorTarget({
                    tenant_id: tenant,
                    customer_name: customer.trim(),
                    year_month: yearMonth,
                    target_revenue: v,
                });
            }
            setSaveMsg("Target saved. Load report below.");
            setReport(null);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Save failed");
        } finally {
            setSaving(false);
        }
    };

    const handleLoadReport = async () => {
        if (!customer.trim()) {
            setError("Select a customer.");
            return;
        }
        setError(null);
        setLoadingReport(true);
        setReport(null);
        try {
            const r = await fetchDistributorVsTarget(tenant, customer.trim(), yearMonth);
            setReport(r);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Report failed");
        } finally {
            setLoadingReport(false);
        }
    };

    const handleDownloadPdf = async () => {
        if (!customer.trim()) {
            setError("Select a customer.");
            return;
        }
        setError(null);
        setPdfLoading(true);
        try {
            const blob = await downloadDistributorVsTargetPdf(tenant, customer.trim(), yearMonth);
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `DistributorVsTarget_${yearMonth}.pdf`;
            a.style.display = "none";
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (e) {
            setError(e instanceof Error ? e.message : "PDF download failed");
        } finally {
            setPdfLoading(false);
        }
    };

    const matRows = Array.isArray(report?.material_groups) ? report.material_groups : [];

    return (
        <div className="space-y-8 max-w-6xl mx-auto">
            <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <Target className="text-[#daa520]" />
                    Distributor vs Target
                </h1>
                <p className="text-gray-400 mt-2 text-sm max-w-3xl leading-relaxed">
                    Set a <strong className="text-gray-300">monthly ₹ target per distributor</strong> (or{" "}
                    <strong className="text-gray-300">% of your company revenue goal</strong> from Executive Summary). The
                    same target is <strong className="text-gray-300">split across material groups</strong> by each
                    group&apos;s share of that customer&apos;s sales in that month — then compare actual vs target here
                    (aligned with your monthly Distributor Strategy Report).
                </p>
            </div>

            {companyGoal != null && companyGoal > 0 ? (
                <p className="text-xs text-gray-500">
                    Company revenue goal (Executive Summary): <span className="text-[#daa520] font-medium">{fmt(companyGoal)}</span>
                </p>
            ) : (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-900/20 border border-amber-700/50 text-sm text-amber-200/90">
                    <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                    <span>
                        Set a <strong>company revenue goal</strong> on <strong>Executive Summary</strong> first if you want to use{" "}
                        <strong>% allocation</strong> (e.g. 30%). You can still save an <strong>absolute ₹</strong> target without it.
                    </span>
                </div>
            )}

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 space-y-4">
                <h2 className="text-lg font-semibold text-white border-b border-[#30363d] pb-3">1. Save monthly target</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
                    <label className="flex flex-col gap-1 text-xs text-gray-400">
                        Month (YYYY-MM)
                        <input
                            type="month"
                            value={yearMonth}
                            onChange={(e) => setYearMonth(e.target.value.slice(0, 7))}
                            className="bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-white text-sm"
                        />
                    </label>
                    <label className="flex flex-col gap-1 text-xs text-gray-400 md:col-span-2">
                        Distributor (customer)
                        <select
                            value={customer}
                            onChange={(e) => setCustomer(e.target.value)}
                            className="bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-white text-sm min-h-[42px]"
                        >
                            <option value="">Select customer…</option>
                            {customerOptions.map((c) => (
                                <option key={c} value={c}>
                                    {c}
                                </option>
                            ))}
                        </select>
                    </label>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
                    <label className="flex flex-col gap-1 text-xs text-gray-400">
                        % of company revenue goal (e.g. 30)
                        <input
                            type="text"
                            inputMode="decimal"
                            value={pctOfCompany}
                            onChange={(e) => {
                                setPctOfCompany(e.target.value);
                                if (e.target.value.trim()) setAbsoluteTarget("");
                            }}
                            placeholder="Leave empty if using ₹ below"
                            className="bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-white text-sm"
                        />
                        {impliedFromPct != null && (
                            <span className="text-[#daa520] text-xs">→ {fmt(impliedFromPct)} / month for this customer</span>
                        )}
                    </label>
                    <label className="flex flex-col gap-1 text-xs text-gray-400">
                        Or absolute ₹ target (month)
                        <input
                            type="text"
                            inputMode="decimal"
                            value={absoluteTarget}
                            onChange={(e) => {
                                setAbsoluteTarget(e.target.value);
                                if (e.target.value.trim()) setPctOfCompany("");
                            }}
                            placeholder="Optional if using % above"
                            className="bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-white text-sm"
                        />
                    </label>
                </div>
                <button
                    type="button"
                    onClick={handleSaveTarget}
                    disabled={saving}
                    className="px-5 py-2.5 rounded-lg bg-[#daa520] text-[#0d1117] font-semibold text-sm hover:opacity-90 disabled:opacity-50"
                >
                    {saving ? (
                        <>
                            <Loader2 className="inline w-4 h-4 animate-spin mr-2" />
                            Saving…
                        </>
                    ) : (
                        "Save target for this month"
                    )}
                </button>
                {saveMsg && <p className="text-sm text-green-400">{saveMsg}</p>}
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 space-y-4">
                <h2 className="text-lg font-semibold text-white border-b border-[#30363d] pb-3">2. Sales vs target (by material group)</h2>
                <p className="text-xs text-gray-500">
                    Uses invoice lines in that calendar month. Material targets = customer target × (group sales ÷ customer sales).
                </p>
                <div className="flex flex-wrap gap-3">
                    <button
                        type="button"
                        onClick={handleLoadReport}
                        disabled={loadingReport}
                        className="px-5 py-2.5 rounded-lg border border-[#daa520]/50 text-[#daa520] font-medium text-sm hover:bg-[#2a2414] disabled:opacity-50"
                    >
                        {loadingReport ? (
                            <>
                                <Loader2 className="inline w-4 h-4 animate-spin mr-2" />
                                Loading…
                            </>
                        ) : (
                            "Load report"
                        )}
                    </button>
                    <button
                        type="button"
                        onClick={handleDownloadPdf}
                        disabled={pdfLoading || !customer.trim()}
                        className="px-5 py-2.5 rounded-lg bg-[#2a2414] border border-[#daa520]/60 text-[#daa520] font-medium text-sm hover:bg-[#332a14] disabled:opacity-50 inline-flex items-center gap-2"
                    >
                        {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        Download PDF
                    </button>
                </div>
                <p className="text-xs text-gray-600">PDF uses the same month and customer as above (saved target required).</p>

                {error && (
                    <div className="p-3 rounded-lg bg-red-900/20 border border-red-800 text-sm text-red-300">{error}</div>
                )}

                {report && !error && (
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            <div className="bg-[#0d1117] rounded-lg p-3 border border-[#30363d]">
                                <div className="text-gray-500 text-xs">Customer actual</div>
                                <div className="text-white font-bold">{fmt(report.customer_actual)}</div>
                            </div>
                            <div className="bg-[#0d1117] rounded-lg p-3 border border-[#30363d]">
                                <div className="text-gray-500 text-xs">Customer target</div>
                                <div className="text-[#daa520] font-bold">{fmt(report.customer_target)}</div>
                            </div>
                            <div className="bg-[#0d1117] rounded-lg p-3 border border-[#30363d]">
                                <div className="text-gray-500 text-xs">Variance</div>
                                <div className={`font-bold ${report.customer_variance >= 0 ? "text-green-400" : "text-red-400"}`}>
                                    {fmt(report.customer_variance)}
                                </div>
                            </div>
                            <div className="bg-[#0d1117] rounded-lg p-3 border border-[#30363d]">
                                <div className="text-gray-500 text-xs">% of target</div>
                                <div className="text-white font-bold">{report.customer_pct_of_target}%</div>
                            </div>
                        </div>
                        {report.message && <p className="text-sm text-amber-300">{report.message}</p>}
                        {matRows.length > 0 && (
                            <DataTable
                                data={matRows}
                                searchable
                                searchPlaceholder="Search material group…"
                                searchKeys={["material_group"]}
                                defaultPageSize={20}
                                pageSizeOptions={[10, 20, 50]}
                                columns={[
                                    { header: "Material group", accessorKey: "material_group", sortable: true },
                                    {
                                        header: "Share of customer",
                                        accessorKey: "share_of_customer_pct",
                                        sortable: true,
                                        align: "right",
                                        cell: (r: any) => <span className="text-gray-300">{Number(r.share_of_customer_pct).toFixed(1)}%</span>,
                                    },
                                    {
                                        header: "Actual",
                                        accessorKey: "actual",
                                        sortable: true,
                                        align: "right",
                                        cell: (r: any) => <span className="text-white font-medium">{fmt(r.actual)}</span>,
                                    },
                                    {
                                        header: "Target",
                                        accessorKey: "target",
                                        sortable: true,
                                        align: "right",
                                        cell: (r: any) => <span className="text-[#daa520]">{fmt(r.target)}</span>,
                                    },
                                    {
                                        header: "Variance",
                                        accessorKey: "variance",
                                        sortable: true,
                                        align: "right",
                                        cell: (r: any) => (
                                            <span className={r.variance >= 0 ? "text-green-400" : "text-red-400"}>{fmt(r.variance)}</span>
                                        ),
                                    },
                                    {
                                        header: "% of target",
                                        accessorKey: "pct_of_target",
                                        sortable: true,
                                        align: "right",
                                        cell: (r: any) => <span className="text-gray-300">{Number(r.pct_of_target).toFixed(0)}%</span>,
                                    },
                                ]}
                            />
                        )}
                    </div>
                )}
            </div>

            <p className="text-xs text-gray-600">
                API: <code className="bg-[#0d1117] px-1 rounded">{API_BASE_URL}/reports/distributor-vs-target</code>
            </p>
        </div>
    );
}
