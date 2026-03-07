"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { API_BASE_URL } from "@/lib/api";

const AUTH_KEY = "elettro_auth";

interface User {
    user: string;
    role: string;
    tenant: string;
}

interface AuthContextType {
    user: User | null;
    login: (username: string, password: string) => Promise<boolean>;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        try {
            const raw = localStorage.getItem(AUTH_KEY);
            if (raw) {
                const parsed = JSON.parse(raw) as User;
                if (parsed?.user) setUser(parsed);
            }
        } catch {
            // ignore
        }
        setIsLoading(false);
    }, []);

    const login = async (username: string, password: string): Promise<boolean> => {
        const base = API_BASE_URL;
        try {
            const res = await fetch(`${base}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: username || "user", password }),
            });
            if (!res.ok) return false;
            const data = await res.json();
            const u = { user: data.user, role: data.role || "viewer", tenant: data.tenant || "default_elettro" };
            setUser(u);
            localStorage.setItem(AUTH_KEY, JSON.stringify(u));
            return true;
        } catch {
            return false;
        }
    };

    const logout = () => {
        setUser(null);
        localStorage.removeItem(AUTH_KEY);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (ctx === undefined) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
}
