"use client";

import { useState, useRef, useEffect } from "react";
import { format } from "date-fns";
import { MessageSquare, X, Send, Loader2 } from "lucide-react";
import { useFilter } from "@/components/FilterContext";
import { API_BASE_URL } from "@/lib/api";

export default function ChatWidget() {
    const { tenant, dateRange } = useFilter();
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<{ role: 'user' | 'bot', content: string }[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom of chat
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg = input.trim();
        setInput("");
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsLoading(true);

        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 30000);
            const res = await fetch(`${API_BASE_URL}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: userMsg,
                    tenant: tenant,
                    startDate: dateRange?.from ? format(dateRange.from, "yyyy-MM-dd") : undefined,
                    endDate: dateRange?.to ? format(dateRange.to, "yyyy-MM-dd") : undefined,
                }),
                signal: controller.signal,
            });
            clearTimeout(timeout);

            if (!res.ok) throw new Error("Failed to reach AI");
            const data = await res.json();
            const reply = typeof data?.response === "string" && data.response.trim()
                ? data.response
                : "No response received from the intelligence engine.";
            setMessages(prev => [...prev, { role: 'bot', content: reply }]);
        } catch (err: any) {
            const msg = err?.name === "AbortError"
                ? "⚠️ Request timed out. The AI engine is taking too long to respond."
                : "⚠️ Sorry, I encountered an error connecting to the intelligence engine.";
            setMessages(prev => [...prev, { role: 'bot', content: msg }]);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 bg-gradient-to-r from-app-gold-hover to-app-gold text-app-on-gold p-4 rounded-full shadow-2xl hover:scale-110 transition-transform z-50 flex items-center justify-center glow-effect"
                title="Open ELETTRO AI"
            >
                <MessageSquare className="w-6 h-6" />
            </button>
        );
    }

    return (
        <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-app-bg border border-app-border rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden font-sans">
            {/* Header */}
            <div className="bg-app-card px-4 py-3 border-b border-app-border flex justify-between items-center">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-app-gold-hover to-app-gold flex items-center justify-center">
                        <MessageSquare className="w-4 h-4 text-app-on-gold" />
                    </div>
                    <div>
                        <h3 className="text-app-fg font-semibold text-sm">ELETTRO AI</h3>
                        <p className="text-xs text-app-fg-muted">Sales Intelligence Assistant</p>
                    </div>
                </div>
                <button onClick={() => setIsOpen(false)} className="text-app-fg-muted hover:text-app-fg transition-colors">
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-app-bg">
                {messages.length === 0 && (
                    <div className="text-center text-app-fg-muted text-sm mt-10">
                        <p>Ask me anything about your current sales data!</p>
                        <ul className="mt-4 space-y-2 text-xs">
                            <li className="bg-app-card py-2 px-3 rounded-lg border border-app-border">"Who are the top 5 customers?"</li>
                            <li className="bg-app-card py-2 px-3 rounded-lg border border-app-border">"What is the total revenue for wires?"</li>
                            <li className="bg-app-card py-2 px-3 rounded-lg border border-app-border">"Total quantity ordered in Delhi"</li>
                        </ul>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${msg.role === 'user'
                            ? 'bg-gradient-to-r from-app-gold-hover to-app-gold text-app-on-gold rounded-br-sm'
                            : 'bg-app-hover border border-app-border text-app-fg rounded-bl-sm'
                            }`}>
                            {msg.content}
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-app-hover border border-app-border rounded-2xl rounded-bl-sm px-4 py-3 flex items-center space-x-2">
                            <Loader2 className="w-4 h-4 text-app-gold animate-spin" />
                            <span className="text-xs text-app-fg-muted">Analyzing database...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-3 bg-app-card border-t border-app-border">
                <div className="relative flex items-center">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Message ELETTRO AI..."
                        className="w-full bg-app-bg border border-app-border rounded-full pl-4 pr-12 py-3 text-sm text-app-fg focus:outline-none focus:border-app-gold transition-colors"
                    />
                    <button
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="absolute right-2 p-2 bg-app-gold text-black rounded-full disabled:opacity-50 disabled:cursor-not-allowed hover:bg-app-gold-hover transition-colors"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
