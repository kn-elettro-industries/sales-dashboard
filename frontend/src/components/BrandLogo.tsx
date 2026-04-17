/**
 * PNG wordmark is built for dark surfaces (white + gold letters).
 * In light mode we sit it on a fixed dark plate so all parts stay visible.
 */
export function BrandLogo({
    size = "md",
    className = "",
}: {
    size?: "sm" | "md" | "lg";
    /** Extra classes on the outer plate wrapper */
    className?: string;
}) {
    const h = size === "sm" ? "h-8" : size === "lg" ? "h-14" : "h-10";
    const pad = size === "sm" ? "px-2 py-1.5" : size === "lg" ? "px-4 py-2.5" : "px-2.5 py-2";
    return (
        <span
            className={`brand-logo-plate inline-flex max-w-full items-center justify-center rounded-lg bg-neutral-950 shadow-md ring-1 ring-black/25 dark:bg-transparent dark:shadow-none dark:ring-0 dark:px-0 dark:py-0 ${pad} ${className}`}
        >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="KN Elettro" className={`${h} w-auto max-w-full object-contain object-left`} />
        </span>
    );
}
