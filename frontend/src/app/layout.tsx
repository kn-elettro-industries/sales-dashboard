import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { AuthProvider } from "@/components/AuthContext";
import { ThemeProvider } from "@/components/ThemeContext";
import LayoutWrapper from "@/components/LayoutWrapper";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "KN Elettro Intelligence",
    description: "Enterprise Sales Reporting Dashboard",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={`${inter.className} bg-app-bg text-app-fg min-h-screen flex`}>
                <Script
                    id="elettro-theme-init"
                    strategy="beforeInteractive"
                    dangerouslySetInnerHTML={{
                        __html: `try{var t=localStorage.getItem("elettro_theme");document.documentElement.classList.remove("light","dark");document.documentElement.classList.add(t==="light"||t==="dark"?t:"dark");}catch(e){document.documentElement.classList.add("dark");}`,
                    }}
                />
                <ThemeProvider>
                    <AuthProvider>
                        <LayoutWrapper>{children}</LayoutWrapper>
                    </AuthProvider>
                </ThemeProvider>
            </body>
        </html>
    );
}
