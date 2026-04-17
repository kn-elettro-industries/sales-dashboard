"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthContext";
import { ThemeCornerToggle } from "@/components/ThemeCornerToggle";

export default function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            const ok = await login(username.trim(), password);
            if (ok) {
                router.replace("/");
            } else {
                setError("Invalid credentials. Please try again.");
            }
        } catch {
            setError("Login failed. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-app-bg p-6">
            <ThemeCornerToggle />
            <div className="w-full max-w-md">
                <div className="text-center mb-8 animate-slide-down opacity-0">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src="/logo.png" alt="ELETTRO" className="h-14 mx-auto object-contain" />
                    <p className="text-app-gold text-sm font-semibold uppercase tracking-[0.25em] mt-4">Intelligence</p>
                </div>

                <div className="bg-app-card border border-app-border rounded-xl p-8 shadow-xl animate-scale-in opacity-0 animation-delay-150">
                    <h1 className="text-xl font-semibold text-app-fg mb-2">Sign in</h1>
                    <p className="text-gray-400 text-sm mb-6">Enter your credentials to access the dashboard.</p>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-gray-400 mb-1">
                                Username
                            </label>
                            <input
                                id="username"
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Enter username"
                                className="w-full bg-app-bg border border-app-border rounded-lg px-4 py-3 text-app-fg placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-app-gold focus:border-transparent transition-all duration-200"
                                autoComplete="username"
                                disabled={loading}
                            />
                        </div>
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-400 mb-1">
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter password"
                                className="w-full bg-app-bg border border-app-border rounded-lg px-4 py-3 text-app-fg placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-app-gold focus:border-transparent transition-all duration-200"
                                autoComplete="current-password"
                                disabled={loading}
                            />
                        </div>
                        {error && (
                            <p className="text-red-400 text-sm animate-fade-in">{error}</p>
                        )}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 rounded-lg bg-app-gold text-app-on-gold font-semibold hover:bg-app-gold-hover hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                        >
                            {loading ? "Signing in..." : "Sign in"}
                        </button>
                        <p className="text-center text-gray-400 text-sm">
                            Don&apos;t have an account?{" "}
                            <Link href="/signup" className="text-app-gold hover:underline font-medium">Sign up</Link>
                        </p>
                    </form>
                </div>

                <p className="text-center text-gray-500 text-xs mt-6 animate-fade-in opacity-0 animation-delay-400">Phase: PROD-1.0 • Cloud ERP</p>
            </div>
        </div>
    );
}
