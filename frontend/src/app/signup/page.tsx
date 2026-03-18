"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthContext";
import { API_BASE_URL } from "@/lib/api";

export default function SignupPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [signupEnabled, setSignupEnabled] = useState<boolean | null>(null);
    const { setUserFromResponse } = useAuth();
    const router = useRouter();

    useEffect(() => {
        fetch(`${API_BASE_URL}/auth/signup-enabled`)
            .then((r) => r.json())
            .then((d) => setSignupEnabled(d.enabled === true))
            .catch(() => setSignupEnabled(false));
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }
        if (password.length < 6) {
            setError("Password must be at least 6 characters.");
            return;
        }
        if (username.trim().length < 2) {
            setError("Username must be at least 2 characters.");
            return;
        }
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE_URL}/auth/signup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username: username.trim(),
                    password,
                    confirm_password: confirmPassword,
                }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                const msg = typeof data.detail === "string" ? data.detail : (Array.isArray(data.detail) ? data.detail[0]?.msg : null);
                setError(msg || "Sign up failed. Please try again.");
                return;
            }
            // Auto-login: signup returns user data
            setUserFromResponse(data);
            router.replace("/");
        } catch {
            setError("Sign up failed. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-[#0d1117] p-6">
            <div className="w-full max-w-md">
                <div className="text-center mb-8 animate-slide-down opacity-0">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src="/logo.png" alt="ELETTRO" className="h-14 mx-auto object-contain" />
                    <p className="text-[#daa520] text-sm font-semibold uppercase tracking-[0.25em] mt-4">Intelligence</p>
                </div>

                <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-8 shadow-xl animate-scale-in opacity-0 animation-delay-150">
                    <h1 className="text-xl font-semibold text-white mb-2">Create account</h1>
                    {signupEnabled === null ? (
                        <p className="text-gray-400 text-sm">Loading...</p>
                    ) : !signupEnabled ? (
                        <>
                            <p className="text-gray-400 text-sm mb-6">
                                Sign up is restricted. Only your administrator can create new accounts.
                            </p>
                            <p className="text-amber-400/90 text-sm mb-6">
                                Contact your administrator to request access.
                            </p>
                            <Link
                                href="/login"
                                className="block w-full py-3 rounded-lg bg-[#daa520] text-[#0d1117] font-semibold hover:bg-[#b8860b] text-center transition-all duration-200"
                            >
                                Back to sign in
                            </Link>
                        </>
                    ) : (
                        <>
                            <p className="text-gray-400 text-sm mb-6">Set your username and password to get started.</p>
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
                                placeholder="Choose a username (min 2 chars)"
                                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#daa520] focus:border-transparent transition-all duration-200"
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
                                placeholder="Min 6 characters"
                                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#daa520] focus:border-transparent transition-all duration-200"
                                autoComplete="new-password"
                                disabled={loading}
                            />
                        </div>
                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-400 mb-1">
                                Confirm password
                            </label>
                            <input
                                id="confirmPassword"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Re-enter password"
                                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#daa520] focus:border-transparent transition-all duration-200"
                                autoComplete="new-password"
                                disabled={loading}
                            />
                        </div>
                        {error && (
                            <p className="text-red-400 text-sm animate-fade-in">{error}</p>
                        )}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 rounded-lg bg-[#daa520] text-[#0d1117] font-semibold hover:bg-[#b8860b] hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                        >
                            {loading ? "Creating account..." : "Sign up"}
                        </button>
                            </form>
                            <p className="text-center text-gray-400 text-sm mt-6">
                                Already have an account?{" "}
                                <Link href="/login" className="text-[#daa520] hover:underline font-medium">
                                    Sign in
                                </Link>
                            </p>
                        </>
                    )}
                </div>

                <p className="text-center text-gray-500 text-xs mt-6 animate-fade-in opacity-0 animation-delay-400">Phase: PROD-1.0 • Cloud ERP</p>
            </div>
        </div>
    );
}
