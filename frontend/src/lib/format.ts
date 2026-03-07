/**
 * Platform-wide number and currency formatting.
 * Indian units: K (Thousand), L (Lakh), Cr (Crore).
 */

/** Format amount in Cr (Crore = 10^7). Use for large totals. */
export function formatCr(value: number): string {
    const n = Number(value) || 0;
    if (n >= 1e7) return `₹ ${(n / 1e7).toFixed(2)} Cr`;
    if (n >= 1e5) return `₹ ${(n / 1e5).toFixed(2)} L`;
    if (n >= 1e3) return `₹ ${(n / 1e3).toFixed(2)} K`;
    return `₹ ${n.toLocaleString("en-IN")}`;
}

/** Format amount in L (Lakh = 10^5). Use for mid-scale. */
export function formatL(value: number): string {
    const n = Number(value) || 0;
    if (n >= 1e5) return `₹ ${(n / 1e5).toFixed(2)} L`;
    if (n >= 1e3) return `₹ ${(n / 1e3).toFixed(2)} K`;
    return `₹ ${n.toLocaleString("en-IN")}`;
}

/** Smart format: Cr / L / K by magnitude. Default for KPIs and tables. */
export function formatAmount(value: number): string {
    const n = Number(value) || 0;
    const abs = Math.abs(n);
    const sign = n < 0 ? "− " : "";
    if (abs >= 1e7) return `${sign}₹ ${(abs / 1e7).toFixed(2)} Cr`;
    if (abs >= 1e5) return `${sign}₹ ${(abs / 1e5).toFixed(2)} L`;
    if (abs >= 1e3) return `${sign}₹ ${(abs / 1e3).toFixed(2)} K`;
    return `${sign}₹ ${abs.toLocaleString("en-IN")}`;
}

/** Compact for chart axes/tooltips: no rupee, just "X.X Cr" / "X L" / "X K". */
export function formatAmountCompact(value: number): string {
    const n = Number(value) || 0;
    const abs = Math.abs(n);
    if (abs >= 1e7) return `${(abs / 1e7).toFixed(1)} Cr`;
    if (abs >= 1e5) return `${(abs / 1e5).toFixed(1)} L`;
    if (abs >= 1e3) return `${(abs / 1e3).toFixed(0)} K`;
    return abs.toLocaleString("en-IN");
}

/** Full en-IN locale for raw display when needed. */
export function formatAmountRaw(value: number): string {
    return `₹ ${(Number(value) || 0).toLocaleString("en-IN")}`;
}

/** Chart Y-axis tick: with rupee, compact (e.g. "₹ 1.5 L"). */
export function formatAxisTick(value: number): string {
    const n = Number(value) || 0;
    const abs = Math.abs(n);
    if (abs >= 1e7) return `₹${(abs / 1e7).toFixed(1)}Cr`;
    if (abs >= 1e5) return `₹${(abs / 1e5).toFixed(0)}L`;
    if (abs >= 1e3) return `₹${(abs / 1e3).toFixed(0)}K`;
    return `₹${abs}`;
}

/** Tooltip: full amount with unit (e.g. "₹ 16.34 Cr"). */
export function formatTooltipAmount(value: number): string {
    return formatAmount(value);
}
