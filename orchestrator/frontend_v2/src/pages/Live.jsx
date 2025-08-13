import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Mic,
  MicOff,
  Send,
  ChevronDown,
  MoreHorizontal,
  Play,
  Pause,
  Volume2,
  VolumeX
} from "lucide-react";

import TimelineView from "../components/live/TimelineView";
import ChatPanel from "../components/live/ChatPanel";
import TelemetryPanel from "../components/live/TelemetryPanel";
import AgentStatusList from "../components/live/AgentStatusList";
import MicControl from "../components/live/MicControl";
import { useAuth } from "@/contexts/AuthContext";
import { useRundown } from "@/contexts/RundownContext";
import { useSocket } from "@/contexts/SocketContext";
import { sendMessage } from "@/api/webSocket";
import { initAudio, stopAudioRecording, playAudio, stopAudioPlayback } from "@/lib/audio";

export default function Live() {
  const [onAirMode, setOnAirMode] = useState(true);
  const [micEnabled, setMicEnabled] = useState(false);
  const [currentMessage, setCurrentMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isAgentReplying, setIsAgentReplying] = useState(false);
  const { currentUser } = useAuth();
  const { rundownSystem } = useRundown();
  const { addEventListener } = useSocket();
  const currentMessageIdRef = useRef(null);

  useEffect(() => {
    if (!currentUser) return;

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
        setIsAgentReplying(false);
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
        setIsAgentReplying(false);
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

    const onOpen = () => {
      console.log("connected");
      // Replace the reconfiguring message with the initial operational message
      setMessages([
        {
          id: "1",
          role: "assistant",
          text: "Connection established",
          timestamp: Date.now(),
          partial: false,
        },
      ]);
    };

    const onClose = () => {
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: `disconnect-message-${Date.now()}`,
          role: 'assistant',
          text: 'Agent connection disconnected',
          timestamp: Date.now(),
          partial: false,
        },
      ]);
    };

    const cleanupMessage = addEventListener('message', onMessage);
    const cleanupOpen = addEventListener('open', onOpen);
    const cleanupClose = addEventListener('close', onClose);


    return () => {
      cleanupMessage();
      cleanupOpen();
      cleanupClose();
    };
  }, [currentUser, rundownSystem, addEventListener]);

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
    setCurrentMessage("");
    setIsAgentReplying(true);

    sendMessage({
      mime_type: 'text/plain',
      data: currentMessage,
    });
  };

  const handleMicToggle = (enabled) => {
    setMicEnabled(enabled);
    if (enabled) {
      initAudio((pcmData) => {
        setIsAgentReplying(true);
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
      {/* Left Panel - Chat & Controls - Responsive */}
      <div className="w-full lg:w-80 bg-[#1C1A22] border-b lg:border-b-0 lg:border-r border-white/8 flex flex-col">
        {/* Header Controls */}
        <div className="p-4 border-b border-white/8">
          <div className="flex items-center gap-3 mb-4">
            <Button
              onClick={() => setOnAirMode(!onAirMode)}
              className={`flex-1 h-10 font-semibold transition-all duration-200 ${
                onAirMode ? "bg-[#FF2D86] hover:bg-[#FF2D86]/90 text-white" : "bg-white/10 hover:bg-white/20 text-[#A6A0AA]"
              }`}
            >
              {onAirMode ? "On-Air" : "Off-Air"}
            </Button>
            <Button variant="outline" size="sm" className="bg-background text-pink-600 px-2 sm:px-3 text-sm font-medium inline-flex items-center justify-center ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-70 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 border border-input hover:bg-accent hover:text-accent-foreground h-9 rounded-md gap-2">
              <span className="hidden sm:inline">Priority</span>
              <ChevronDown className="w-3 h-3" />
            </Button>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <Badge variant="outline" className="text-[#A6A0AA] text-xs">All items</Badge>
            <Button variant="ghost" size="sm" className="text-[#A6A0AA] hover:text-[#E6E1E5] text-xs">
              Clear All
            </Button>
          </div>
        </div>

        {/* Chat Panel - Responsive height */}
        <div className="flex-1 overflow-hidden min-h-[200px] lg:min-h-0">
          <ChatPanel messages={messages} isAgentReplying={isAgentReplying} />
        </div>

        {/* Input Controls */}
        <div className="p-4 border-t border-white/8 space-y-4">
          <MicControl enabled={micEnabled} onToggle={handleMicToggle} />
          
          <div className="flex gap-2">
            <Input
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              placeholder="Send message to agents..."
              className="bg-white/5 border-white/10 text-[#E6E1E5] placeholder:text-[#A6A0AA] text-sm"
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            />
            <Button
              onClick={handleSendMessage}
              size="icon"
              className="bg-[#FF2D86] hover:bg-[#FF2D86]/90 flex-shrink-0"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Center Panel - Timeline - Responsive */}
      <div className="flex-1 overflow-auto min-h-[400px] lg:min-h-0">
        <TimelineView />
      </div>

      {/* Right Panel - Telemetry & Agents - Hidden on mobile, collapsible on tablet */}
      <div className="hidden md:flex w-full md:w-80 lg:w-80 bg-[#1C1A22] border-t md:border-t-0 md:border-l border-white/8 flex-col">
        <div className="flex-1 overflow-hidden">
          <TelemetryPanel />
        </div>
        <div className="border-t border-white/8">
          <AgentStatusList />
        </div>
      </div>
    </div>
  );
}