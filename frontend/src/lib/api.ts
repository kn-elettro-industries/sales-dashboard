/** When true, browser calls same-origin /api/proxy so CORS is never an issue. Set on Vercel if you hit CORS. */
const USE_PROXY = process.env.NEXT_PUBLIC_USE_API_PROXY === "true" || process.env.NEXT_PUBLIC_USE_API_PROXY === "1";

/** Base URL for the API (trimmed; no trailing slash). Use proxy when NEXT_PUBLIC_USE_API_PROXY=true to avoid CORS. */
export const API_BASE_URL = USE_PROXY
    ? "/api/proxy"
    : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").trim().replace(/\/+$/, "");

/** Client cache: 5 min TTL so navigation feels instant and reduces backend load. */
const CACHE_TTL_MS = 5 * 60 * 1000;
/** Timeout for API requests (backend cold start on Render can be 30–60s). */
const FETCH_TIMEOUT_MS = 50 * 1000;
const apiCache = new Map<string, { data: unknown; expiresAt: number }>();

function getCached<T>(key: string): T | null {
    const entry = apiCache.get(key);
    if (!entry || Date.now() > entry.expiresAt) return null;
    return entry.data as T;
}

function setCached(key: string, data: unknown) {
    apiCache.set(key, { data, expiresAt: Date.now() + CACHE_TTL_MS });
}

function fetchWithTimeout(url: string, init?: RequestInit, timeoutMs = FETCH_TIMEOUT_MS): Promise<Response> {
    const ac = new AbortController();
    const id = setTimeout(() => ac.abort(), timeoutMs);
    return fetch(url, { ...init, signal: ac.signal }).finally(() => clearTimeout(id));
}

type FilterParams = {
    tenant?: string;
    startDate?: string;
    endDate?: string;
    days?: string;
    states?: string;
    cities?: string;
    customers?: string;
    materialGroups?: string;
    fiscalYears?: string;
    months?: string;
    goalRevenue?: number;
    goalOrders?: number;
};

function buildQueryString(params: FilterParams = {}) {
    const query = new URLSearchParams();
    if (params.tenant) query.append("tenant_id", params.tenant);
    if (params.startDate) query.append("start_date", params.startDate);
    if (params.endDate) query.append("end_date", params.endDate);
    if (params.days) query.append("days", params.days);
    if (params.states) query.append("states", params.states);
    if (params.cities) query.append("cities", params.cities);
    if (params.customers) query.append("customers", params.customers);
    if (params.materialGroups) query.append("material_groups", params.materialGroups);
    if (params.fiscalYears) query.append("fiscal_years", params.fiscalYears);
    if (params.months) query.append("months", params.months);
    if (params.goalRevenue != null && params.goalRevenue > 0) query.append("goal_revenue", String(params.goalRevenue));
    if (params.goalOrders != null && params.goalOrders > 0) query.append("goal_orders", String(params.goalOrders));

    const str = query.toString();
    return str ? `?${str}` : "";
}

async function apiFetch(path: string, params?: FilterParams) {
    const qs = buildQueryString(params);
    const key = `${path}${qs}`;
    const cached = getCached(key);
    if (cached !== null) return cached;
    const url = `${API_BASE_URL}${path}${qs}`;
    const res = await fetchWithTimeout(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
    const data = await res.json();
    setCached(key, data);
    return data;
}

// Executive Summary (other pages: swallow errors so they get empty data)
export const fetchKpiSummary = (p?: FilterParams) => apiFetch("/metrics/summary", p).catch(() => null);
export const fetchSalesTrend = (p?: FilterParams) => apiFetch("/charts/trend", p).then(d => d || []).catch(() => []);
export const fetchMaterialGroups = (p?: FilterParams) => apiFetch("/charts/material-groups", p).then(d => d || []).catch(() => []);
export const fetchTopCustomers = (p?: FilterParams) => apiFetch("/charts/top-customers", p).then(d => d || []).catch(() => []);

// Single dashboard payload (throws on failure so dashboard can show "slow/unreachable" + retry)
export const fetchDashboardSummary = (p?: FilterParams) => apiFetch("/dashboard/summary", p);

// Sales & Growth
export const fetchMonthlySales = (p?: FilterParams) => apiFetch("/sales/monthly", p).then(d => d || []).catch(() => []);
export const fetchDailySales = (days = 30, p?: FilterParams) => apiFetch(`/sales/daily${buildQueryString({ ...p, days: days.toString() })}`).then(d => d || []).catch(() => []);
export const fetchGrowthMetrics = (p?: FilterParams) => apiFetch("/sales/growth", p).catch(() => null);

// Customer Intelligence
export const fetchAllCustomers = (p?: FilterParams) => apiFetch("/customers/all", p).then(d => d || []).catch(() => []);
export const fetchRfmSegments = (p?: FilterParams) => apiFetch("/customers/rfm", p).then(d => d || []).catch(() => []);

// Geographic
export const fetchStateData = (p?: FilterParams) => apiFetch("/geographic/states", p).then(d => d || []).catch(() => []);
export const fetchCityData = (p?: FilterParams) => apiFetch("/geographic/cities", p).then(d => d || []).catch(() => []);

// Material Performance
export const fetchMaterialPerformance = (p?: FilterParams) => apiFetch("/materials/performance", p).then(d => d || []).catch(() => []);
export const fetchParetoData = (p?: FilterParams) => apiFetch("/materials/pareto", p).then(d => d || []).catch(() => []);

// Reports
export const fetchItemDetails = (p?: FilterParams) => apiFetch("/reports/item-details", p).then(d => d || []).catch(() => []);

// Data quality (with timeout)
export const fetchDataHealth = (tenant?: string) =>
    fetchWithTimeout(`${API_BASE_URL}/data/health?tenant_id=${tenant || "default_elettro"}`, { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);

// Anomalies (alerts) — uses timeout; returns empty on error so dashboard still renders
export const fetchAnomalies = (p?: FilterParams & { dropThresholdPct?: number }) => {
    const params = new URLSearchParams();
    if (p?.tenant) params.append("tenant_id", p.tenant);
    if (p?.startDate) params.append("start_date", p.startDate);
    if (p?.endDate) params.append("end_date", p.endDate);
    if (p?.states) params.append("states", p.states);
    if (p?.customers) params.append("customers", p.customers);
    if (p?.materialGroups) params.append("material_groups", p.materialGroups);
    if (p?.fiscalYears) params.append("fiscal_years", p.fiscalYears);
    if (p?.months) params.append("months", p.months);
    if (p?.dropThresholdPct != null) params.append("drop_threshold_pct", String(p.dropThresholdPct));
    const url = `${API_BASE_URL}/analytics/anomalies?${params.toString()}`;
    return fetchWithTimeout(url, { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : { anomalies: [] }))
        .catch(() => ({ anomalies: [] }));
};
