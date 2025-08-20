import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send } from "lucide-react";
import ChatPanel from "../components/live/ChatPanel";
import TelemetryPanel from "../components/live/TelemetryPanel";
import MicControl from "../components/live/MicControl";
import { useRundown } from "@/contexts/useRundown";
import { useSocket } from "@/contexts/useSocket";
import { sendMessage } from "@/api/webSocket";
import { initAudio, stopAudioRecording, playAudio, stopAudioPlayback } from "@/lib/audio";

export default function Console() {
  const { rundownSystem } = useRundown();
  const [currentMessage, setCurrentMessage] = useState("");
  const [micEnabled, setMicEnabled] = useState(false);
  const [messages, setMessages] = useState([]);
  const { addEventListener, connectionStatus } = useSocket();
  const currentMessageIdRef = useRef(null);

  useEffect(() => {
    if (connectionStatus === 'connected') {
        setMessages([
            {
              id: "welcome-message",
              role: "assistant",
              text: "Full console mode active. How can I assist with your broadcast?",
              timestamp: Date.now(),
              partial: false,
            },
          ]);
    } else if (connectionStatus === 'connecting') {
        setMessages(prev => {
            if (prev.length > 0 && prev[prev.length - 1].id === 'connecting-message') return prev;
            return [...prev, {
                id: 'connecting-message',
                role: 'assistant',
                text: 'Connecting...',
                timestamp: Date.now(),
                partial: false,
            }];
        });
    } else if (connectionStatus === 'disconnected') {
        setMessages(prev => {
            if (prev.length > 0 && prev[prev.length - 1].id === 'disconnected-message') return prev;
            return [...prev, {
                id: 'disconnected-message',
                role: 'assistant',
                text: 'Connection lost. Attempting to reconnect...',
                timestamp: Date.now(),
                partial: false,
            }];
        });
    }
  }, [connectionStatus]);

  useEffect(() => {
    // Clear messages and show a reconfiguring message when rundownSystem changes
    setMessages([
      {
        id: 'reconfiguring-message',
        role: 'assistant',
        text: `Reconfiguring for ${rundownSystem.toUpperCase()}...`,
        timestamp: Date.now(),
        partial: false,
      },
    ]);

    const onMessage = (message) => {
      if (message.turn_complete) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === currentMessageIdRef.current ? { ...msg, partial: false } : msg
          )
        );
        currentMessageIdRef.current = null;
        return;
      }

      if (message.interrupted) {
        stopAudioPlayback();
        return;
      }

      if (message.mime_type === 'audio/pcm') {
        playAudio(message.data);
      }

      if (message.mime_type === 'text/plain') {
        setMessages((prevMessages) => {
          const existingMsg = prevMessages.find(msg => msg.id === currentMessageIdRef.current);
          if (existingMsg) {
            return prevMessages.map((msg) =>
              msg.id === currentMessageIdRef.current
                ? { ...msg, text: msg.text + message.data }
                : msg
            );
          } else {
            currentMessageIdRef.current = `agent-message-${Date.now()}`;
            return [
              ...prevMessages,
              {
                id: currentMessageIdRef.current,
                role: 'assistant',
                text: message.data,
                timestamp: Date.now(),
                partial: true,
              },
            ];
          }
        });
      }
    };

    const cleanupMessage = addEventListener('message', onMessage);

    return () => {
      cleanupMessage();
    };
  }, [rundownSystem, addEventListener]);

  const handleSendMessage = () => {
    if (!currentMessage.trim()) return;

    const newMessage = {
      id: Date.now().toString(),
      role: "user",
      text: currentMessage,
      timestamp: Date.now(),
      partial: false,
    };

    setMessages((prev) => [...prev, newMessage]);
    sendMessage({
      mime_type: 'text/plain',
      data: currentMessage,
    });
    setCurrentMessage("");
  };

  const handleMicToggle = (enabled) => {
    setMicEnabled(enabled);
    if (enabled) {
      initAudio((pcmData) => {
        sendMessage({
          mime_type: 'audio/pcm',
          data: pcmData,
        });
      });
    } else {
      stopAudioRecording();
    }
  };

  return (
    <div className="h-[calc(100vh-80px)] flex flex-col lg:flex-row">
      {/* Main Chat Area - Responsive */}
      <div className="flex-1 flex flex-col bg-[#0D0B12]">
        {/* Header */}
        <div className="p-4 sm:p-6 border-b border-white/8 flex justify-between items-center">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#E6E1E5]">Assistant Console</h1>
            <p className="text-[#A6A0AA] mt-1 text-sm">Full conversation mode with streaming transcript</p>
          </div>
        </div>

        {/* Chat Messages - Responsive */}
        <div className="flex-1 overflow-hidden">
          <div className="h-full p-4 sm:p-6">
            <ChatPanel messages={messages} />
          </div>
        </div>

        {/* Input Area - Responsive */}
        <div className="border-t border-white/8 p-4 sm:p-6">
          <div className="max-w-4xl mx-auto space-y-4">
            <MicControl enabled={micEnabled} onToggle={handleMicToggle} />

            <div className="flex flex-col sm:flex-row gap-4">
              <Textarea
                value={currentMessage}
                onChange={(e) => setCurrentMessage(e.target.value)}
                placeholder="Type your message to the AI assistant..."
                className="flex-1 bg-white/5 border-white/10 text-[#E6E1E5] placeholder:text-[#A6A0AA] min-h-[100px] resize-none text-sm"
                onKeyPress={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
              />
              <div className="flex sm:flex-col gap-2">
                <Button
                  onClick={handleSendMessage}
                  className="bg-[#FF2D86] hover:bg-[#FF2D86]/90 h-12 px-4 sm:px-8 flex-1 sm:flex-none"
                >
                  <Send className="w-4 h-4 mr-2" />
                  Send
                </Button>
                <p className="text-xs text-[#A6A0AA] text-center hidden sm:block">
                  Enter to send<br />Shift+Enter for new line
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar - Telemetry - Hidden on mobile */}
      {/* <div className="hidden lg:block w-80 bg-[#1C1A22] border-l border-white/8">
        <TelemetryPanel />
      </div> */}
    </div>
  );
}
