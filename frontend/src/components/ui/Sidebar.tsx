"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, TrendingUp, Users, Package, MapPin, ShieldAlert, FileText, Database, LogIn, LogOut, UserPlus, Moon, Sun } from "lucide-react";
import { useAuth } from "@/components/AuthContext";
import { useTheme } from "@/components/ThemeContext";

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
    const { theme, toggleTheme, mounted } = useTheme();
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
        <aside className="w-64 bg-app-card border-r border-app-border flex flex-col h-screen sticky top-0">
            <div className="p-5 border-b border-app-border flex flex-col items-start">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.png" alt="KN Elettro" className="h-10 object-contain" />
                <span className="text-app-gold text-xs font-semibold uppercase tracking-[0.25em] mt-2">KN Elettro Intelligence</span>
            </div>

            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                {navItems.map((group) => (
                    <div key={group.section}>
                        <div className="text-xs font-semibold text-app-fg-muted uppercase tracking-wider mb-2 mt-4">{group.section}</div>
                        {group.items.map((item) => {
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 mb-1 ${isActive
                                        ? "bg-app-gold text-app-on-gold font-medium"
                                        : "text-app-fg-muted hover:bg-app-muted hover:text-app-fg"
                                        }`}
                                >
                                    <item.icon className="h-5 w-5" />
                                    <span className="text-sm">{item.label}</span>
                                </Link>
                            );
                        })}
                    </div>
                ))}
                {(user?.role || "").toLowerCase() === "admin" && (
                    <div>
                        <div className="text-xs font-semibold text-app-fg-muted uppercase tracking-wider mb-2 mt-4">Admin</div>
                        <Link
                            href="/admin"
                            className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 mb-1 ${pathname === "/admin"
                                ? "bg-app-gold text-app-on-gold font-medium"
                                : "text-app-fg-muted hover:bg-app-muted hover:text-app-fg"
                                }`}
                        >
                            <UserPlus className="h-5 w-5" />
                            <span className="text-sm">Add user</span>
                        </Link>
                    </div>
                )}
            </nav>

            <div className="p-4 border-t border-app-border text-sm text-app-fg-muted space-y-2">
                <button
                    type="button"
                    onClick={toggleTheme}
                    className="flex w-full items-center justify-between gap-2 rounded-lg border border-app-border bg-app-hover px-3 py-2 text-app-fg-muted transition-colors hover:border-app-gold/40 hover:text-app-fg"
                    title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                    aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                >
                    <span className="text-xs font-medium uppercase tracking-wide">Theme</span>
                    <span className="flex items-center gap-1.5 text-app-gold">
                        {!mounted ? (
                            <Moon className="h-4 w-4 opacity-50" />
                        ) : theme === "dark" ? (
                            <>
                                <Sun className="h-4 w-4" />
                                <span className="text-[11px] text-app-fg-muted">Light</span>
                            </>
                        ) : (
                            <>
                                <Moon className="h-4 w-4" />
                                <span className="text-[11px] text-app-fg-muted">Dark</span>
                            </>
                        )}
                    </span>
                </button>
                {user ? (
                    <>
                        <p className="text-app-fg-muted truncate" title={user.user}>{user.user} <span className="text-app-gold">({user.role})</span></p>
                        <button type="button" onClick={logout} className="flex items-center gap-2 text-red-400 hover:text-red-300">
                            <LogOut size={14} /> Log out
                        </button>
                    </>
                ) : showLogin ? (
                    <div className="space-y-2">
                        <input type="text" placeholder="Username" value={uname} onChange={(e) => setUname(e.target.value)} className="w-full bg-app-bg border border-app-border rounded px-2 py-1 text-app-fg text-sm" />
                        <input type="password" placeholder="Password" value={pwd} onChange={(e) => setPwd(e.target.value)} className="w-full bg-app-bg border border-app-border rounded px-2 py-1 text-app-fg text-sm" />
                        {loginErr && <p className="text-red-400 text-xs">Login failed</p>}
                        <div className="flex gap-2">
                            <button type="button" onClick={handleLogin} className="flex-1 py-1 rounded bg-app-gold text-app-on-gold text-xs font-medium">Log in</button>
                            <button type="button" onClick={() => { setShowLogin(false); setLoginErr(false); }} className="py-1 px-2 rounded border border-app-border text-app-fg-muted text-xs">Cancel</button>
                        </div>
                    </div>
                ) : (
                    <button type="button" onClick={() => setShowLogin(true)} className="flex items-center gap-2 text-app-gold hover:text-app-gold-hover">
                        <LogIn size={14} /> Log in
                    </button>
                )}
                <p>Phase: PROD-1.0</p>
                <p>Connected: Cloud ERP</p>
            </div>
        </aside>
    );
}
