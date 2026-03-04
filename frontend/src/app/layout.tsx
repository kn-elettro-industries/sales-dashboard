import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { LayoutDashboard, TrendingUp, Users, Package, FileText, Settings, ShieldAlert } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "ELETTRO Intelligence",
    description: "Enterprise Sales Reporting Dashboard",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={`${inter.className} bg-[var(--color-brand-dark)] text-gray-200 min-h-screen flex`}>

                {/* Sidebar */}
                <aside className="w-64 bg-[var(--color-brand-card)] border-r border-[var(--color-brand-border)] flex flex-col h-screen sticky top-0">
                    <div className="p-6 border-b border-[var(--color-brand-border)]">
                        <h1 className="text-xl font-bold flex flex-col">
                            <span className="text-white tracking-widest">ELETTRO</span>
                            <span className="text-[var(--color-brand-gold)] text-sm font-normal uppercase tracking-widest mt-1">Intelligence</span>
                        </h1>
                    </div>

                    <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 mt-4">Dashboards</div>
                        <NavItem icon={LayoutDashboard} label="Executive Summary" active />
                        <NavItem icon={TrendingUp} label="Sales & Growth" />
                        <NavItem icon={Users} label="Customer Intelligence" />
                        <NavItem icon={Package} label="Material Performance" />

                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 mt-8">Operations</div>
                        <NavItem icon={ShieldAlert} label="Risk Management" />
                        <NavItem icon={FileText} label="Industrial Reporting" />
                        <NavItem icon={Settings} label="System Settings" />
                    </nav>

                    <div className="p-4 border-t border-[var(--color-brand-border)] text-sm text-gray-500">
                        <p>Phase: PROD-1.0</p>
                        <p>Connected: Cloud ERP</p>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="flex-1 min-h-screen flex flex-col">
                    <header className="h-16 bg-[var(--color-brand-card)] border-b border-[var(--color-brand-border)] flex items-center justify-between px-8 sticky top-0 z-10">
                        <h2 className="text-lg font-semibold text-white">Production Manager View</h2>
                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-gray-400">Last Synced: Just now</span>
                            <div className="h-8 w-8 rounded-full bg-[var(--color-brand-gold)] text-[var(--color-brand-dark)] flex items-center justify-center font-bold">
                                AD
                            </div>
                        </div>
                    </header>

                    <div className="p-8 flex-1 overflow-y-auto">
                        {children}
                    </div>
                </main>
            </body>
        </html>
    );
}

function NavItem({ icon: Icon, label, active = false }: { icon: any, label: string, active?: boolean }) {
    return (
        <a href="#" className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${active ? 'bg-[var(--color-brand-gold)] text-[var(--color-brand-dark)] font-medium' : 'text-gray-400 hover:bg-[#2d333b] hover:text-white'}`}>
            <Icon className="h-5 w-5" />
            <span>{label}</span>
        </a>
    );
}
