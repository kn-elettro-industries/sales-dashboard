import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/AuthContext";
import LayoutWrapper from "@/components/LayoutWrapper";

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
                    <LayoutWrapper>{children}</LayoutWrapper>
                </AuthProvider>
            </body>
        </html>
    );
}
