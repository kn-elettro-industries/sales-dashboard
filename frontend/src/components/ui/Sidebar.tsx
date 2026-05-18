"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard, TrendingUp, Users, Package, MapPin, ShieldAlert,
    FileText, Database, LogIn, LogOut, UserPlus, Moon, Sun, User, Zap,
} from "lucide-react";
import { useAuth } from "@/components/AuthContext";
import { useTheme } from "@/components/ThemeContext";
import { BrandLogo } from "@/components/BrandLogo";

const navGroups = [
    {
        section: "Dashboards",
        items: [
            { href: "/",           label: "Executive Summary",       icon: LayoutDashboard },
            { href: "/sales",      label: "Sales & Growth",          icon: TrendingUp },
            { href: "/customers",  label: "Customer Intelligence",   icon: Users },
            { href: "/materials",  label: "Material Performance",    icon: Package },
        ],
    },
    {
        section: "Operations",
        items: [
            { href: "/geographic", label: "Geographic Intelligence", icon: MapPin },
            { href: "/risk",       label: "Risk Management",         icon: ShieldAlert },
            { href: "/data",       label: "Cloud Data Uploader",     icon: Database },
            { href: "/reports",    label: "Industrial Reporting",    icon: FileText },
        ],
    },
];

function NavItem({ href, label, icon: Icon, isActive }: { href: string; label: string; icon: React.ElementType; isActive: boolean }) {
    return (
        <Link
            href={href}
            className={`relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 group
                ${isActive
                    ? "bg-app-gold/10 text-app-gold font-semibold"
                    : "text-app-fg-muted hover:bg-app-muted hover:text-app-fg"
                }`}
        >
            {/* Left accent bar */}
            <span className={`absolute left-0 inset-y-[18%] w-[3px] rounded-r-full bg-app-gold
                transition-all duration-300 origin-center
                ${isActive ? "opacity-100 scale-y-100" : "opacity-0 scale-y-0"}`}
            />
            <Icon className={`h-4 w-4 shrink-0 transition-colors ${isActive ? "text-app-gold" : "group-hover:text-app-fg"}`} />
            <span className="truncate">{label}</span>
        </Link>
    );
}

function SectionLabel({ title }: { title: string }) {
    return (
        <div className="flex items-center gap-2 px-2 mb-1.5 mt-5 first:mt-2">
            <div className="h-px flex-1 bg-app-border" />
            <span className="text-[10px] font-bold text-app-fg-muted uppercase tracking-[0.14em] shrink-0">{title}</span>
            <div className="h-px flex-1 bg-app-border" />
        </div>
    );
}

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
        if (ok) { setShowLogin(false); setUname(""); setPwd(""); }
        else setLoginErr(true);
    };

    return (
        <aside className="w-64 shrink-0 bg-app-card border-r border-app-border flex flex-col h-screen sticky top-0">

            {/* ── Brand ── */}
            <div className="px-4 py-4 border-b border-app-border">
                <BrandLogo size="md" />
                <p className="text-[10px] text-app-fg-muted mt-2 tracking-[0.18em] uppercase font-medium pl-0.5">
                    Intelligence Platform
                </p>
            </div>

            {/* ── Navigation ── */}
            <nav className="flex-1 px-3 py-2 overflow-y-auto">
                {navGroups.map((group) => (
                    <div key={group.section}>
                        <SectionLabel title={group.section} />
                        <div className="space-y-0.5">
                            {group.items.map((item) => (
                                <NavItem
                                    key={item.href}
                                    href={item.href}
                                    label={item.label}
                                    icon={item.icon}
                                    isActive={pathname === item.href}
                                />
                            ))}
                        </div>
                    </div>
                ))}

                {(user?.role || "").toLowerCase() === "admin" && (
                    <div>
                        <SectionLabel title="Admin" />
                        <NavItem href="/admin" label="Add user" icon={UserPlus} isActive={pathname === "/admin"} />
                    </div>
                )}
            </nav>

            {/* ── Footer ── */}
            <div className="px-3 pb-4 pt-3 border-t border-app-border space-y-2.5">

                {/* Theme toggle */}
                <button
                    type="button"
                    onClick={toggleTheme}
                    className="flex w-full items-center justify-between rounded-lg border border-app-border bg-app-bg px-3 py-2 text-sm text-app-fg-muted hover:border-app-gold/40 hover:text-app-fg transition-all duration-200"
                >
                    <span className="text-xs">{!mounted ? "Theme" : theme === "dark" ? "Light mode" : "Dark mode"}</span>
                    {!mounted
                        ? <Moon className="h-3.5 w-3.5 opacity-40" />
                        : theme === "dark"
                            ? <Sun  className="h-3.5 w-3.5 text-app-gold" />
                            : <Moon className="h-3.5 w-3.5 text-app-gold" />}
                </button>

                {/* User info / login */}
                {user ? (
                    <div className="flex items-center gap-2.5 rounded-lg bg-app-bg border border-app-border px-3 py-2.5">
                        <div className="h-8 w-8 rounded-full bg-app-gold/15 border border-app-gold/25 flex items-center justify-center shrink-0">
                            <User className="h-3.5 w-3.5 text-app-gold" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-app-fg truncate leading-tight">{user.user}</p>
                            <p className="text-[10px] text-app-gold capitalize leading-tight mt-0.5">{user.role}</p>
                        </div>
                        <button type="button" onClick={logout} title="Log out"
                            className="text-app-fg-muted hover:text-red-400 transition-colors p-1 rounded-md hover:bg-red-900/20">
                            <LogOut className="h-3.5 w-3.5" />
                        </button>
                    </div>
                ) : showLogin ? (
                    <div className="rounded-lg bg-app-bg border border-app-border p-3 space-y-2">
                        <input type="text" placeholder="Username" value={uname}
                            onChange={(e) => setUname(e.target.value)}
                            className="w-full bg-transparent border border-app-border rounded-md px-2.5 py-1.5 text-app-fg text-xs placeholder:text-app-fg-muted focus:outline-none focus:border-app-gold transition-colors" />
                        <input type="password" placeholder="Password" value={pwd}
                            onChange={(e) => setPwd(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                            className="w-full bg-transparent border border-app-border rounded-md px-2.5 py-1.5 text-app-fg text-xs placeholder:text-app-fg-muted focus:outline-none focus:border-app-gold transition-colors" />
                        {loginErr && <p className="text-red-400 text-xs">Invalid credentials</p>}
                        <div className="flex gap-2">
                            <button type="button" onClick={handleLogin}
                                className="flex-1 py-1.5 rounded-md bg-app-gold text-app-on-gold text-xs font-semibold hover:opacity-90 transition-opacity">
                                Sign in
                            </button>
                            <button type="button" onClick={() => { setShowLogin(false); setLoginErr(false); }}
                                className="py-1.5 px-2.5 rounded-md border border-app-border text-app-fg-muted text-xs hover:bg-app-muted transition-colors">
                                Cancel
                            </button>
                        </div>
                    </div>
                ) : (
                    <button type="button" onClick={() => setShowLogin(true)}
                        className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-app-fg-muted hover:bg-app-muted hover:text-app-gold transition-all duration-200">
                        <LogIn className="h-4 w-4" />
                        <span>Sign in</span>
                    </button>
                )}

                {/* Status row */}
                <div className="flex items-center justify-between px-1 pt-0.5">
                    <span className="text-[10px] text-app-fg-muted font-mono">PROD-1.0</span>
                    <span className="flex items-center gap-1.5 text-[10px] text-green-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse-slow" />
                        Cloud ERP
                    </span>
                </div>
            </div>
        </aside>
    );
}
