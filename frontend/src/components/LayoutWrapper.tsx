"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import Sidebar from "@/components/ui/Sidebar";
import GlobalFilterBar from "@/components/ui/GlobalFilterBar";
import ChatWidget from "@/components/ui/ChatWidget";
import { FilterProvider } from "@/components/FilterContext";
import { useAuth } from "@/components/AuthContext";
import { OnboardingBanner } from "@/components/OnboardingBanner";
import { ClientKeyboardShortcuts } from "@/components/ClientKeyboardShortcuts";

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const { user, isLoading } = useAuth();
    const isLoginPage = pathname === "/login";
    const isSignupPage = pathname === "/signup";

    useEffect(() => {
        if (isLoading) return;
        if ((isLoginPage || isSignupPage) && user) {
            router.replace("/");
            return;
        }
        if (!isLoginPage && !isSignupPage && !user) {
            router.replace("/login");
        }
    }, [isLoading, user, isLoginPage, isSignupPage, router]);

    if (isLoginPage || isSignupPage) {
        return (
            <div className="min-h-screen w-full flex">
                {children}
            </div>
        );
    }

    if (!user) {
        return (
            <div className="min-h-screen w-full flex items-center justify-center">
                <div className="animate-shimmer text-gray-500 text-sm">Loading...</div>
            </div>
        );
    }

    return (
        <FilterProvider>
            <Sidebar />
            <main className="flex-1 min-h-screen flex flex-col">
                <GlobalFilterBar />
                <OnboardingBanner />
                <ClientKeyboardShortcuts />
                <div className="p-8 flex-1 overflow-y-auto">
                    {children}
                </div>
            </main>
            <ChatWidget />
        </FilterProvider>
    );
}
