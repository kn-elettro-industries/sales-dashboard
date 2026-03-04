import { KpiCard } from "@/components/ui/KpiCard";
import { BarChart, PieChart } from "@/components/ui/Charts";
import { fetchKpiSummary, fetchSalesTrend, fetchMaterialGroups, fetchTopCustomers } from "@/lib/api";
import { DollarSign, ShoppingCart, Users, TrendingUp } from "lucide-react";

export default async function Dashboard() {
    const [summary, trend, groups, customers] = await Promise.all([
        fetchKpiSummary().catch(() => ({ revenue: 0, orders: 0, customers: 0, average_order_value: 0 })),
        fetchSalesTrend().catch(() => []),
        fetchMaterialGroups().catch(() => []),
        fetchTopCustomers().catch(() => [])
    ]);

    const validTrend = Array.isArray(trend) ? trend : [];
    const validGroups = Array.isArray(groups) ? groups : [];
    const validCustomers = Array.isArray(customers) ? customers : [];

    const formatCurrency = (val: number) => `₹ ${(val || 0).toLocaleString('en-IN')}`;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">

            <div>
                <h2 className="text-2xl font-bold text-white">Fiscal Year Overview</h2>
                <p className="text-gray-400 mt-1">Real-time performance metrics and sales trends.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <KpiCard
                    title="Total Revenue"
                    value={formatCurrency(summary.revenue)}
                    icon={DollarSign}
                    trend="12.5%"
                    trendUp={true}
                />
                <KpiCard
                    title="Total Orders"
                    value={(summary.orders || 0).toLocaleString()}
                    icon={ShoppingCart}
                    trend="4.2%"
                    trendUp={true}
                />
                <KpiCard
                    title="Unique Customers"
                    value={(summary.customers || 0).toLocaleString()}
                    icon={Users}
                    trend="2.1%"
                    trendUp={false}
                />
                <KpiCard
                    title="Avg Order Value"
                    value={formatCurrency(summary.average_order_value)}
                    icon={TrendingUp}
                    trend="8.4%"
                    trendUp={true}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 bg-[var(--color-brand-card)] border border-[var(--color-brand-border)] rounded-xl p-6 shadow-sm">
                    <div className="flex justify-between items-center border-b border-[#30363d] pb-4">
                        <div>
                            <h3 className="text-lg font-semibold text-white">Monthly Sales Trend</h3>
                            <p className="text-xs text-gray-400 mt-1">Revenue over the current fiscal year</p>
                        </div>
                    </div>
                    {validTrend.length > 0 ? (
                        <BarChart data={validTrend} xKey="DATE" yKey="AMOUNT" />
                    ) : (
                        <div className="h-80 flex items-center justify-center text-gray-500">No trend data available</div>
                    )}
                </div>

                <div className="bg-[var(--color-brand-card)] border border-[var(--color-brand-border)] rounded-xl p-6 shadow-sm">
                    <div className="border-b border-[#30363d] pb-4">
                        <h3 className="text-lg font-semibold text-white">Top Material Groups</h3>
                        <p className="text-xs text-gray-400 mt-1">By revenue share</p>
                    </div>
                    {validGroups.length > 0 ? (
                        <PieChart
                            data={validGroups.slice(0, 5)}
                            nameKey={Object.keys(validGroups[0] || {}).find(k => k !== 'AMOUNT') || 'MATERIALGROUP'}
                            valueKey="AMOUNT"
                        />
                    ) : (
                        <div className="h-80 flex items-center justify-center text-gray-500">No category data</div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ListCard title="Top Customers" data={validCustomers} valueKey="AMOUNT" nameKey="CUSTOMER_NAME" />
                <ListCard title="Top Performers (Material Groups)" data={validGroups} valueKey="AMOUNT" nameKey={validGroups.length > 0 ? Object.keys(validGroups[0] || {}).find(k => k !== 'AMOUNT') || 'MATERIALGROUP' : 'MATERIALGROUP'} />
            </div>

        </div>
    );
}

function ListCard({ title, data, valueKey, nameKey }: { title: string, data: any[], valueKey: string, nameKey: string }) {
    const formatCurrency = (val: number) => `₹ ${(val || 0).toLocaleString('en-IN')}`;

    return (
        <div className="bg-[var(--color-brand-card)] border border-[var(--color-brand-border)] rounded-xl p-6 shadow-sm flex flex-col">
            <h3 className="text-lg font-semibold text-white border-b border-[#30363d] pb-4 mb-4">{title}</h3>
            <div className="flex-1 overflow-y-auto pr-2" style={{ maxHeight: '250px' }}>
                <table className="w-full text-sm text-left text-gray-400">
                    <tbody>
                        {data.slice(0, 10).map((item, idx) => (
                            <tr key={idx} className="border-b border-[#2d333b] last:border-0 hover:bg-[#2d333b] transition-colors">
                                <td className="py-3 px-2 text-gray-300 font-medium">{item[nameKey]?.slice(0, 40) || 'Unknown'}</td>
                                <td className="py-3 px-2 text-right text-white font-semibold">{formatCurrency(item[valueKey])}</td>
                            </tr>
                        ))}
                        {data.length === 0 && (
                            <tr><td colSpan={2} className="py-4 text-center">No data available</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
