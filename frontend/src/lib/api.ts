const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api";

export async function fetchKpiSummary(tenantId = "default_elettro") {
    const res = await fetch(`${API_BASE_URL}/metrics/summary?tenant_id=${tenantId}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch KPIs");
    return res.json();
}

export async function fetchSalesTrend(tenantId = "default_elettro") {
    const res = await fetch(`${API_BASE_URL}/charts/trend?tenant_id=${tenantId}`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
}

export async function fetchMaterialGroups(tenantId = "default_elettro") {
    const res = await fetch(`${API_BASE_URL}/charts/material-groups?tenant_id=${tenantId}`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
}

export async function fetchTopCustomers(tenantId = "default_elettro") {
    const res = await fetch(`${API_BASE_URL}/charts/top-customers?tenant_id=${tenantId}`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
}
