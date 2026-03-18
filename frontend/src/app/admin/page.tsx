"use client";

import { useState } from "react";
import { useAuth } from "@/components/AuthContext";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";
import { UserPlus, Shield } from "lucide-react";

export default function AdminPage() {
    const { user } = useAuth();
    const router = useRouter();
    const [newUsername, setNewUsername] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [adminPassword, setAdminPassword] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [loading, setLoading] = useState(false);

    const isAdmin = (user?.role || "").toLowerCase() === "admin";

    if (!user) {
        router.replace("/login");
        return null;
    }

    if (!isAdmin) {
        return (
            <div className="min-h-[50vh] flex items-center justify-center p-6">
                <div className="text-center text-gray-400">
                    <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="font-medium">Admin access required.</p>
                    <p className="text-sm mt-1">Only administrators can add new users.</p>
                </div>
            </div>
        );
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccess("");
        if (!newUsername.trim() || newUsername.trim().length < 2) {
            setError("Username must be at least 2 characters.");
            return;
        }
        if (!newPassword || newPassword.length < 6) {
            setError("Password must be at least 6 characters.");
            return;
        }
        if (!adminPassword) {
            setError("Enter your password to confirm.");
            return;
        }
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE_URL}/admin/create-user`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username: newUsername.trim(),
                    password: newPassword,
                    admin_username: user.user,
                    admin_password: adminPassword,
                }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                setError(typeof data.detail === "string" ? data.detail : "Failed to create user.");
                return;
            }
            setSuccess(`User "${newUsername}" created. They can sign in now.`);
            setNewUsername("");
            setNewPassword("");
            setAdminPassword("");
        } catch {
            setError("Failed to create user.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-lg mx-auto p-6">
            <div className="flex items-center gap-3 mb-6">
                <UserPlus className="h-8 w-8 text-[#daa520]" />
                <div>
                    <h1 className="text-xl font-semibold text-white">Add user</h1>
                    <p className="text-gray-400 text-sm">Create accounts for your team.</p>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-400 mb-1">New username</label>
                    <input
                        type="text"
                        value={newUsername}
                        onChange={(e) => setNewUsername(e.target.value)}
                        placeholder="e.g. sales1"
                        className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#daa520]"
                        disabled={loading}
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-400 mb-1">New password</label>
                    <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="Min 6 characters"
                        className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#daa520]"
                        disabled={loading}
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-400 mb-1">Your password (to confirm)</label>
                    <input
                        type="password"
                        value={adminPassword}
                        onChange={(e) => setAdminPassword(e.target.value)}
                        placeholder="Enter your admin password"
                        className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#daa520]"
                        disabled={loading}
                    />
                </div>
                {error && <p className="text-red-400 text-sm">{error}</p>}
                {success && <p className="text-green-400 text-sm">{success}</p>}
                <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 rounded-lg bg-[#daa520] text-[#0d1117] font-semibold hover:bg-[#b8860b] disabled:opacity-50 transition-all"
                >
                    {loading ? "Creating..." : "Create user"}
                </button>
            </form>
        </div>
    );
}
