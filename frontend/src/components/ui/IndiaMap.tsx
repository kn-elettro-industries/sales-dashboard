"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { formatCr } from "@/lib/format";
import "leaflet/dist/leaflet.css";

interface StateData {
    STATE: string;
    Revenue: number;
    Revenue_Cr: number;
    Orders: number;
    Customers: number;
    MarketShare: number;
    lat: number;
    lon: number;
}

interface IndiaMapProps {
    states: StateData[];
    onStateClick?: (state: string) => void;
}

// Gradient palette — dark navy to vivid gold/white
function getColor(ratio: number): string {
    if (ratio > 0.8) return "#FFD700";
    if (ratio > 0.6) return "#e6b800";
    if (ratio > 0.4) return "#cc8400";
    if (ratio > 0.2) return "#995500";
    if (ratio > 0.1) return "#663300";
    if (ratio > 0.05) return "#3d2200";
    return "#1a1a2e";
}

// Map GeoJSON state names to uppercase database names
function normalizeStateName(name: string): string {
    return name.toUpperCase().trim();
}

export default function IndiaMap({ states, onStateClick }: IndiaMapProps) {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstance = useRef<L.Map | null>(null);
    const [hoveredState, setHoveredState] = useState<string | null>(null);

    useEffect(() => {
        if (!mapRef.current) return;

        let destroyed = false;

        // Destroy previous map
        if (mapInstance.current) {
            mapInstance.current.remove();
            mapInstance.current = null;
        }

        // Create map
        const map = L.map(mapRef.current, {
            center: [22.5, 82.0],
            zoom: 5,
            scrollWheelZoom: true,
            zoomControl: false,
            attributionControl: false,
            minZoom: 4,
            maxZoom: 8,
        });

        mapInstance.current = map;

        // Zoom control top-right
        L.control.zoom({ position: "topright" }).addTo(map);

        // Ultra-dark base layer
        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png", {
            maxZoom: 19,
        }).addTo(map);

        // Custom attribution
        L.control.attribution({ prefix: "ELETTRO Intelligence" }).addTo(map);

        // Build revenue lookup
        const revenueLookup: Record<string, StateData> = {};
        let maxRevenue = 0;
        states.forEach(s => {
            const key = normalizeStateName(s.STATE);
            revenueLookup[key] = s;
            if (s.Revenue > maxRevenue) maxRevenue = s.Revenue;
        });

        // Load GeoJSON (async — must guard against unmount)
        fetch("/india-states.geojson")
            .then(r => r.json())
            .then((geoData) => {
                // Guard: if component unmounted during fetch, do nothing
                if (destroyed || !mapInstance.current) return;

                const geoLayer = L.geoJSON(geoData, {
                    style: (feature) => {
                        const stateName = normalizeStateName(feature?.properties?.NAME_1 || "");
                        const stateData = revenueLookup[stateName];
                        const ratio = stateData ? stateData.Revenue / maxRevenue : 0;
                        const fillColor = getColor(ratio);

                        return {
                            fillColor,
                            weight: 1,
                            opacity: 0.8,
                            color: "#FFD70040",
                            fillOpacity: stateData ? 0.75 : 0.15,
                        };
                    },
                    onEachFeature: (feature, layer) => {
                        const stateName = normalizeStateName(feature?.properties?.NAME_1 || "");
                        const stateData = revenueLookup[stateName];

                        // Tooltip
                        if (stateData) {
                            layer.bindTooltip(
                                `<div style="font-family: 'Inter', system-ui, sans-serif; min-width: 180px;">
                                    <div style="font-size: 14px; font-weight: 700; color: #FFD700; margin-bottom: 6px; border-bottom: 1px solid #30363d; padding-bottom: 6px;">
                                        ${stateData.STATE}
                                    </div>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; font-size: 12px;">
                                        <span style="color: #8b949e;">Revenue</span>
                                        <span style="color: #f0f6fc; font-weight: 600; text-align: right;">${formatCr(stateData.Revenue)}</span>
                                        <span style="color: #8b949e;">Market Share</span>
                                        <span style="color: #daa520; font-weight: 600; text-align: right;">${stateData.MarketShare}%</span>
                                        <span style="color: #8b949e;">Orders</span>
                                        <span style="color: #f0f6fc; font-weight: 600; text-align: right;">${stateData.Orders?.toLocaleString()}</span>
                                        <span style="color: #8b949e;">Customers</span>
                                        <span style="color: #f0f6fc; font-weight: 600; text-align: right;">${stateData.Customers}</span>
                                    </div>
                                </div>`,
                                {
                                    direction: "auto",
                                    className: "choropleth-tooltip",
                                    sticky: true,
                                }
                            );
                        } else {
                            layer.bindTooltip(
                                `<div style="font-family: 'Inter', sans-serif; font-size: 12px; color: #8b949e;">
                                    ${feature?.properties?.NAME_1 || "Unknown"}<br/>
                                    <span style="font-size: 11px; color: #555;">No sales data</span>
                                </div>`,
                                { direction: "auto", className: "choropleth-tooltip", sticky: true }
                            );
                        }

                        // Hover effects
                        layer.on({
                            mouseover: (e: any) => {
                                const l = e.target;
                                l.setStyle({
                                    weight: 2,
                                    color: "#FFD700",
                                    fillOpacity: stateData ? 0.9 : 0.3,
                                });
                                l.bringToFront();
                                setHoveredState(stateName);
                            },
                            mouseout: (e: any) => {
                                geoLayer.resetStyle(e.target);
                                setHoveredState(null);
                            },
                            click: () => {
                                if (stateData && onStateClick) {
                                    onStateClick(stateData.STATE);
                                }
                            },
                        });
                    },
                });

                // Final guard before adding to map
                if (!destroyed && mapInstance.current) {
                    geoLayer.addTo(mapInstance.current);
                }
            })
            .catch((err) => {
                if (!destroyed) console.error("Failed to load GeoJSON:", err);
            });

        return () => {
            destroyed = true;
            if (mapInstance.current) {
                mapInstance.current.remove();
                mapInstance.current = null;
            }
        };
    }, [states, onStateClick]);

    return (
        <div className="relative">
            <style jsx global>{`
                .choropleth-tooltip {
                    background: rgba(13, 17, 23, 0.95) !important;
                    backdrop-filter: blur(12px) !important;
                    border: 1px solid #30363d !important;
                    border-radius: 10px !important;
                    color: #f0f6fc !important;
                    padding: 10px 14px !important;
                    font-size: 12px !important;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 20px rgba(218,165,32,0.1) !important;
                }
                .choropleth-tooltip::before {
                    display: none !important;
                }
                .leaflet-container {
                    background: #0d1117 !important;
                }
            `}</style>

            <div ref={mapRef} style={{ height: "550px", width: "100%", borderRadius: "12px", overflow: "hidden" }} />

            {/* Gradient Legend */}
            <div className="absolute bottom-4 left-4 bg-[#0d1117]/90 backdrop-blur-md border border-[#30363d] rounded-lg px-4 py-3 z-[1000]">
                <div className="text-[10px] text-gray-400 uppercase tracking-wider mb-2 font-medium">Revenue Intensity</div>
                <div className="flex items-center gap-1">
                    <span className="text-[10px] text-gray-500">Low</span>
                    <div className="flex h-3 rounded-sm overflow-hidden">
                        {["#1a1a2e", "#3d2200", "#663300", "#995500", "#cc8400", "#e6b800", "#FFD700"].map((c, i) => (
                            <div key={i} style={{ backgroundColor: c, width: "24px", height: "12px" }} />
                        ))}
                    </div>
                    <span className="text-[10px] text-gray-500">High</span>
                </div>
            </div>

            {/* Info Badge */}
            <div className="absolute top-4 left-4 bg-[#0d1117]/80 backdrop-blur-md border border-[#30363d] rounded-lg px-3 py-2 z-[1000]">
                <div className="text-xs text-gray-400">
                    <span className="text-[#daa520] font-semibold">{states.length}</span> states •{" "}
                    Hover to inspect • Click to drill down
                </div>
            </div>
        </div>
    );
}
