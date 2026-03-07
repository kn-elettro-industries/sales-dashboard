"use client";

import { useState, useRef, useEffect } from "react";
import { MessageSquare, X, Send, Loader2 } from "lucide-react";
import { useFilter } from "@/components/FilterContext";

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
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: userMsg,
                    tenant: tenant,
                    startDate: dateRange?.from?.toISOString(),
                    endDate: dateRange?.to?.toISOString()
                })
            });

            if (!res.ok) throw new Error("Failed to reach AI");
            const data = await res.json();

            setMessages(prev => [...prev, { role: 'bot', content: data.response }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'bot', content: "⚠️ Sorry, I encountered an error connecting to the intelligence engine." }]);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 bg-gradient-to-r from-[#b8860b] to-[#daa520] text-black p-4 rounded-full shadow-2xl hover:scale-110 transition-transform z-50 flex items-center justify-center glow-effect"
                title="Open ELETTRO AI"
            >
                <MessageSquare className="w-6 h-6" />
            </button>
        );
    }

    return (
        <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-[#0d1117] border border-[#30363d] rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden font-sans">
            {/* Header */}
            <div className="bg-[#161b22] px-4 py-3 border-b border-[#30363d] flex justify-between items-center">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-[#b8860b] to-[#daa520] flex items-center justify-center">
                        <MessageSquare className="w-4 h-4 text-black" />
                    </div>
                    <div>
                        <h3 className="text-white font-semibold text-sm">ELETTRO AI</h3>
                        <p className="text-xs text-gray-400">Sales Intelligence Assistant</p>
                    </div>
                </div>
                <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white transition-colors">
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#0d1117]">
                {messages.length === 0 && (
                    <div className="text-center text-gray-500 text-sm mt-10">
                        <p>Ask me anything about your current sales data!</p>
                        <ul className="mt-4 space-y-2 text-xs">
                            <li className="bg-[#161b22] py-2 px-3 rounded-lg border border-[#30363d]">"Who are the top 5 customers?"</li>
                            <li className="bg-[#161b22] py-2 px-3 rounded-lg border border-[#30363d]">"What is the total revenue for wires?"</li>
                            <li className="bg-[#161b22] py-2 px-3 rounded-lg border border-[#30363d]">"Total quantity ordered in Delhi"</li>
                        </ul>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${msg.role === 'user'
                            ? 'bg-gradient-to-r from-[#b8860b] to-[#daa520] text-black rounded-br-sm'
                            : 'bg-[#21262d] border border-[#30363d] text-gray-200 rounded-bl-sm'
                            }`}>
                            {msg.content}
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-[#21262d] border border-[#30363d] rounded-2xl rounded-bl-sm px-4 py-3 flex items-center space-x-2">
                            <Loader2 className="w-4 h-4 text-[#daa520] animate-spin" />
                            <span className="text-xs text-gray-400">Analyzing database...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-3 bg-[#161b22] border-t border-[#30363d]">
                <div className="relative flex items-center">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Message ELETTRO AI..."
                        className="w-full bg-[#0d1117] border border-[#30363d] rounded-full pl-4 pr-12 py-3 text-sm text-white focus:outline-none focus:border-[#daa520] transition-colors"
                    />
                    <button
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="absolute right-2 p-2 bg-[#daa520] text-black rounded-full disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#b8860b] transition-colors"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
