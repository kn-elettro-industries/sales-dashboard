"use client";

import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, FileSpreadsheet, CheckCircle2, AlertCircle, Loader2, Activity } from "lucide-react";
import { useFilter } from "@/components/FilterContext";
import { fetchDataHealth } from "@/lib/api";

export default function DataUploadPage() {
    const { tenant } = useFilter();
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
    const [message, setMessage] = useState("");
    const [health, setHealth] = useState<{ total_rows: number; missing_dates: number; duplicate_invoices: number; negative_amounts: number; score: number; status: string; message: string } | null>(null);
    const [healthLoading, setHealthLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        setHealthLoading(true);
        fetchDataHealth(tenant).then((d) => {
            if (!cancelled && d) setHealth(d);
        }).finally(() => { if (!cancelled) setHealthLoading(false); });
        return () => { cancelled = true; };
    }, [tenant, status]);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            setFile(acceptedFiles[0]);
            setStatus("idle");
            setMessage("");
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
            "application/vnd.ms-excel": [".xls"],
            "text/csv": [".csv"]
        },
        maxFiles: 1
    });

    const handleUpload = async () => {
        if (!file) return;

        setStatus("uploading");

        const formData = new FormData();
        formData.append("file", file);
        formData.append("tenant_id", tenant);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/upload`, {
                method: "POST",
                body: formData,
            });

            const result = await response.json();

            if (response.ok) {
                setStatus("success");
                setMessage(`Successfully processed ${result.rows_inserted || 0} rows into the database.`);
                setFile(null);
            } else {
                setStatus("error");
                setMessage(result.detail || "Upload failed. Please check the file format.");
            }
        } catch (error) {
            setStatus("error");
            setMessage("A network error occurred while uploading. Ensure the backend is running.");
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div>
                <h2 className="text-2xl font-bold text-white">Cloud Data Management</h2>
                <p className="text-gray-400 mt-1">Upload raw sales data (Excel/CSV) and monitor data quality.</p>
            </div>

            {/* Data Quality */}
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Activity className="h-5 w-5 text-[#daa520]" />
                    Data Quality Health
                </h3>
                {healthLoading ? (
                    <div className="flex items-center gap-2 text-gray-400">
                        <Loader2 className="h-5 w-5 animate-spin" /> Loading...
                    </div>
                ) : health ? (
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        <div className="bg-[#0d1117] rounded-lg p-4 border border-[#30363d]">
                            <p className="text-xs text-gray-500 uppercase">Total Rows</p>
                            <p className="text-xl font-bold text-white">{health.total_rows.toLocaleString()}</p>
                        </div>
                        <div className="bg-[#0d1117] rounded-lg p-4 border border-[#30363d]">
                            <p className="text-xs text-gray-500 uppercase">Missing Dates</p>
                            <p className="text-xl font-bold text-white">{health.missing_dates.toLocaleString()}</p>
                        </div>
                        <div className="bg-[#0d1117] rounded-lg p-4 border border-[#30363d]">
                            <p className="text-xs text-gray-500 uppercase">Duplicate Rows</p>
                            <p className="text-xl font-bold text-white">{health.duplicate_invoices.toLocaleString()}</p>
                        </div>
                        <div className="bg-[#0d1117] rounded-lg p-4 border border-[#30363d]">
                            <p className="text-xs text-gray-500 uppercase">Negative Amounts</p>
                            <p className="text-xl font-bold text-white">{health.negative_amounts.toLocaleString()}</p>
                        </div>
                        <div className="bg-[#0d1117] rounded-lg p-4 border border-[#30363d]">
                            <p className="text-xs text-gray-500 uppercase">Quality Score</p>
                            <p className={`text-xl font-bold ${health.status === "good" ? "text-green-400" : health.status === "warning" ? "text-yellow-400" : "text-red-400"}`}>{health.score}/100</p>
                        </div>
                    </div>
                ) : (
                    <p className="text-gray-500">Unable to load data health.</p>
                )}
                {health?.message && <p className="text-sm text-gray-400 mt-3">{health.message}</p>}
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-8">
                <div className="mb-6 flex items-center justify-between border-b border-[#30363d] pb-4">
                    <div>
                        <h3 className="text-lg font-semibold text-white">Upload Pipeline</h3>
                        <p className="text-sm text-gray-400">Targeting Tenant: <span className="text-[#daa520] font-medium">{tenant}</span></p>
                    </div>
                    <div className="text-sm px-3 py-1 bg-[#0d1117] border border-[#30363d] rounded-md text-gray-400">
                        Accepts: .xlsx, .xls, .csv
                    </div>
                </div>

                {/* Drag and Drop Zone */}
                <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
            ${isDragActive ? 'border-[#daa520] bg-[#daa520]/10' : 'border-[#30363d] hover:border-gray-500 hover:bg-[#21262d]'}
            ${file ? 'border-green-500/50 bg-green-500/5' : ''}
          `}
                >
                    <input {...getInputProps()} />
                    <UploadCloud className={`mx-auto h-16 w-16 mb-4 ${isDragActive ? 'text-[#daa520]' : file ? 'text-green-500' : 'text-gray-500'}`} />

                    {file ? (
                        <div className="space-y-2">
                            <p className="text-lg font-medium text-white">{file.name}</p>
                            <p className="text-sm text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            <p className="text-lg font-medium text-white">Drag & drop your file here, or click to select</p>
                            <p className="text-sm text-gray-500">Must follow the standard ELETTRO data schema</p>
                        </div>
                    )}
                </div>

                {/* Status Messages */}
                {status === "success" && (
                    <div className="mt-6 p-4 bg-green-900/20 border border-green-900 rounded-lg flex items-start gap-3">
                        <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0 mt-0.5" />
                        <div>
                            <h4 className="text-green-500 font-medium">Upload Successful</h4>
                            <p className="text-sm text-green-400/80 mt-1">{message}</p>
                        </div>
                    </div>
                )}

                {status === "error" && (
                    <div className="mt-6 p-4 bg-red-900/20 border border-red-900 rounded-lg flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                        <div>
                            <h4 className="text-red-500 font-medium">Upload Failed</h4>
                            <p className="text-sm text-red-400/80 mt-1">{message}</p>
                        </div>
                    </div>
                )}

                {/* Action Button */}
                <div className="mt-8 flex justify-end">
                    <button
                        onClick={handleUpload}
                        disabled={!file || status === "uploading"}
                        className={`flex items-center px-6 py-2.5 rounded-lg font-medium transition-all
              ${!file || status === "uploading"
                                ? 'bg-[#30363d] text-gray-500 cursor-not-allowed'
                                : 'bg-[#daa520] text-[#0d1117] hover:bg-[#b8860b] hover:shadow-lg hover:shadow-[#daa520]/20'
                            }
            `}
                    >
                        {status === "uploading" ? (
                            <>
                                <Loader2 className="animate-spin h-5 w-5 mr-2" />
                                Processing Data...
                            </>
                        ) : (
                            <>
                                <FileSpreadsheet className="h-5 w-5 mr-2" />
                                Upload to Database
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
