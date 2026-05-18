export function BrandLogo({
    size = "md",
    className = "",
}: {
    size?: "sm" | "md" | "lg";
    className?: string;
}) {
    const h = size === "sm" ? "h-8" : size === "lg" ? "h-14" : "h-10";
    const pad = size === "sm" ? "px-2 py-0.5" : size === "lg" ? "px-4 py-1.5" : "px-3 py-1";
    return (
        <span
            className={`inline-flex max-w-full items-center justify-center rounded-xl bg-[#111111] ${pad} ${className}`}
        >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
                src="/elettro-logo.svg"
                alt="KN Elettro"
                className={`${h} w-auto max-w-full object-contain object-left`}
            />
        </span>
    );
}
