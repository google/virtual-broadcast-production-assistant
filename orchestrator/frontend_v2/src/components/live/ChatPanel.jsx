import React, { useRef, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";

export default function ChatPanel({ messages, isAgentReplying }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isAgentReplying]);

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-white/8">
        <h3 className="font-semibold text-[#E6E1E5]">Assistant Chat</h3>
      </div>
      
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl p-3 ${
              message.role === 'user'
                ? 'bg-[#FF2D86] text-white'
                : 'bg-white/10 text-[#E6E1E5]'
            }`}>
              <p className="text-sm">{message.text}</p>
              <div className="text-xs opacity-70 mt-1">
                {format(new Date(message.timestamp), 'HH:mm')}
              </div>
            </div>
          </div>
        ))}
        {isAgentReplying && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl p-3 bg-white/10 text-[#E6E1E5]">
              <div className="flex items-center gap-2 mt-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
                  <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}