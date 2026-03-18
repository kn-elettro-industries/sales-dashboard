"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { API_BASE_URL } from "@/lib/api";

const AUTH_KEY = "elettro_auth";
const AUTH_TOKEN_KEY = "elettro_token";

interface User {
    user: string;
    role: string;
    tenant: string;
    token?: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (username: string, password: string) => Promise<boolean>;
    setUserFromResponse: (data: { user: string; role?: string; tenant?: string; token?: string }) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        try {
            const raw = localStorage.getItem(AUTH_KEY);
            const tok = localStorage.getItem(AUTH_TOKEN_KEY);
            if (raw) {
                const parsed = JSON.parse(raw) as User;
                if (parsed?.user) setUser(parsed);
            }
            if (tok) setToken(tok);
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
                body: JSON.stringify({ username: username.trim(), password }),
            });
            if (!res.ok) return false;
            const data = await res.json();
            const u = { user: data.user, role: data.role || "viewer", tenant: data.tenant || "default_elettro" };
            setUser(u);
            localStorage.setItem(AUTH_KEY, JSON.stringify(u));
            if (data.token) {
                setToken(data.token);
                localStorage.setItem(AUTH_TOKEN_KEY, data.token);
            }
            return true;
        } catch {
            return false;
        }
    };

    const logout = () => {
        setUser(null);
        setToken(null);
        localStorage.removeItem(AUTH_KEY);
        localStorage.removeItem(AUTH_TOKEN_KEY);
    };

    const setUserFromResponse = (data: { user: string; role?: string; tenant?: string; token?: string }) => {
        const u = { user: data.user, role: data.role || "viewer", tenant: data.tenant || "default_elettro" };
        setUser(u);
        localStorage.setItem(AUTH_KEY, JSON.stringify(u));
        if (data.token) {
            setToken(data.token);
            localStorage.setItem(AUTH_TOKEN_KEY, data.token);
        }
    };

    return (
        <AuthContext.Provider value={{ user, token, login, setUserFromResponse, logout, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (ctx === undefined) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
}
