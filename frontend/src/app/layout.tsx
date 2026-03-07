import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/ui/Sidebar";
import GlobalFilterBar from "@/components/ui/GlobalFilterBar";
import ChatWidget from "@/components/ui/ChatWidget";
import { FilterProvider } from "@/components/FilterContext";
import { AuthProvider } from "@/components/AuthContext";
import { OnboardingBanner } from "@/components/OnboardingBanner";
import { ClientKeyboardShortcuts } from "@/components/ClientKeyboardShortcuts";

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
            <body className={`${inter.className} bg-[#0d1117] text-gray-200 min-h-screen flex`}>
                <AuthProvider>
                    <FilterProvider>
                        <Sidebar />
                    <main className="flex-1 min-h-screen flex flex-col">
                        <GlobalFilterBar />
                        <OnboardingBanner />
                        <ClientKeyboardShortcuts />
                        {/* Chat Widget Wrapper */}
                        <div className="p-8 flex-1 overflow-y-auto">
                            {children}
                        </div>
                    </main>
                    <ChatWidget />
                </FilterProvider>
                </AuthProvider>
            </body>
        </html>
    );
}
