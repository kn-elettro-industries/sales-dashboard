"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, TrendingUp, Users, Package, MapPin, ShieldAlert, FileText, Database, LogIn, LogOut } from "lucide-react";
import { useAuth } from "@/components/AuthContext";

const navItems = [
    {
        section: "Dashboards", items: [
            { href: "/", label: "Executive Summary", icon: LayoutDashboard },
            { href: "/sales", label: "Sales & Growth", icon: TrendingUp },
            { href: "/customers", label: "Customer Intelligence", icon: Users },
            { href: "/materials", label: "Material Performance", icon: Package },
        ]
    },
    {
        section: "Operations", items: [
            { href: "/geographic", label: "Geographic Intelligence", icon: MapPin },
            { href: "/risk", label: "Risk Management", icon: ShieldAlert },
            { href: "/data", label: "Cloud Data Uploader", icon: Database },
            { href: "/reports", label: "Industrial Reporting", icon: FileText },
        ]
    },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { user, login, logout } = useAuth();
    const [showLogin, setShowLogin] = useState(false);
    const [uname, setUname] = useState("");
    const [pwd, setPwd] = useState("");
    const [loginErr, setLoginErr] = useState(false);

    const handleLogin = async () => {
        setLoginErr(false);
        const ok = await login(uname, pwd);
        if (ok) {
            setShowLogin(false);
            setUname("");
            setPwd("");
        } else setLoginErr(true);
    };

    return (
        <aside className="w-64 bg-[#161b22] border-r border-[#30363d] flex flex-col h-screen sticky top-0">
            <div className="p-5 border-b border-[#30363d] flex flex-col items-start">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.png" alt="ELETTRO" className="h-10 object-contain" />
                <span className="text-[#daa520] text-xs font-semibold uppercase tracking-[0.25em] mt-2">Intelligence</span>
            </div>

            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                {navItems.map((group) => (
                    <div key={group.section}>
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 mt-4">{group.section}</div>
                        {group.items.map((item) => {
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 mb-1 ${isActive
                                        ? "bg-[#daa520] text-[#0d1117] font-medium"
                                        : "text-gray-400 hover:bg-[#2d333b] hover:text-white"
                                        }`}
                                >
                                    <item.icon className="h-5 w-5" />
                                    <span className="text-sm">{item.label}</span>
                                </Link>
                            );
                        })}
                    </div>
                ))}
            </nav>

            <div className="p-4 border-t border-[#30363d] text-sm text-gray-500 space-y-2">
                {user ? (
                    <>
                        <p className="text-gray-400 truncate" title={user.user}>{user.user} <span className="text-[#daa520]">({user.role})</span></p>
                        <button type="button" onClick={logout} className="flex items-center gap-2 text-red-400 hover:text-red-300">
                            <LogOut size={14} /> Log out
                        </button>
                    </>
                ) : showLogin ? (
                    <div className="space-y-2">
                        <input type="text" placeholder="Username" value={uname} onChange={(e) => setUname(e.target.value)} className="w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1 text-white text-sm" />
                        <input type="password" placeholder="Password" value={pwd} onChange={(e) => setPwd(e.target.value)} className="w-full bg-[#0d1117] border border-[#30363d] rounded px-2 py-1 text-white text-sm" />
                        {loginErr && <p className="text-red-400 text-xs">Login failed</p>}
                        <div className="flex gap-2">
                            <button type="button" onClick={handleLogin} className="flex-1 py-1 rounded bg-[#daa520] text-[#0d1117] text-xs font-medium">Log in</button>
                            <button type="button" onClick={() => { setShowLogin(false); setLoginErr(false); }} className="py-1 px-2 rounded border border-[#30363d] text-gray-400 text-xs">Cancel</button>
                        </div>
                    </div>
                ) : (
                    <button type="button" onClick={() => setShowLogin(true)} className="flex items-center gap-2 text-[#daa520] hover:text-[#b8860b]">
                        <LogIn size={14} /> Log in
                    </button>
                )}
                <p>Phase: PROD-1.0</p>
                <p>Connected: Cloud ERP</p>
            </div>
        </aside>
    );
}
