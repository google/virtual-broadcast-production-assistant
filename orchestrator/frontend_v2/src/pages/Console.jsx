import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send } from "lucide-react";
import ChatPanel from "../components/live/ChatPanel";
import TelemetryPanel from "../components/live/TelemetryPanel";
import MicControl from "../components/live/MicControl";
import { useAuth } from "@/contexts/AuthContext";
import { db } from "@/lib/firebase";
import { doc, getDoc, setDoc } from "firebase/firestore";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { initApi } from "@/api/webSocket";
import { initAudio, stopAudioRecording, playAudio, stopAudioPlayback } from "@/lib/audio";

export default function Console() {
  const { currentUser } = useAuth();
  const [currentMessage, setCurrentMessage] = useState("");
  const [micEnabled, setMicEnabled] = useState(false);
  const [rundownSystem, setRundownSystem] = useState("cuez");
  const [messages, setMessages] = useState([]);
  const [api, setApi] = useState(null);
  const currentMessageIdRef = useRef(null);

  useEffect(() => {
    if (!currentUser) return;

    const userDocRef = doc(db, "user_preferences", currentUser.uid);

    const getRundownSystem = async () => {
      try {
        const docSnap = await getDoc(userDocRef);
        if (docSnap.exists()) {
          setRundownSystem(docSnap.data().rundown_system);
        } else {
          await setDoc(userDocRef, { rundown_system: "cuez" });
        }
      } catch (error) {
        console.error("Error getting rundown system preference:", error);
      }
    };

    getRundownSystem();
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser || !currentUser.uid) return;

    function getToken() {
      return currentUser.getIdToken();
    }

    const newApi = initApi(
      {
        onConnect: () => {
          console.log("WebSocket connected");
          setMessages([
            {
              id: "1",
              role: "assistant",
              text: "Full console mode active. How can I assist with your broadcast?",
              timestamp: Date.now(),
              partial: false,
            },
          ]);
        },
        onDisconnect: () => {
          console.log("WebSocket disconnected");
        },
        onMessage: (message) => {
          if (message.turn_complete) {
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
              if (currentMessageIdRef.current === null) {
                currentMessageIdRef.current = `agent-message-${Date.now()}`;
                return [
                  ...prevMessages,
                  {
                    id: currentMessageIdRef.current,
                    role: 'agent',
                    text: message.data,
                    timestamp: Date.now(),
                    partial: true,
                  },
                ];
              } else {
                return prevMessages.map((msg) =>
                  msg.id === currentMessageIdRef.current
                    ? { ...msg, text: msg.text + message.data }
                    : msg
                );
              }
            });
          }
        },
      },
      micEnabled,
      currentUser.uid,
      getToken
    );

    setApi(newApi);

    return () => {
      newApi.disconnect();
    };
  }, [currentUser, rundownSystem, micEnabled]);

  const handleRundownChange = async (checked) => {
    if (!currentUser) return;
    const newRundownSystem = checked ? "sofie" : "cuez";
    setRundownSystem(newRundownSystem);
    const userDocRef = doc(db, "user_preferences", currentUser.uid);
    try {
      await setDoc(userDocRef, { rundown_system: newRundownSystem }, { merge: true });
    } catch (error) {
      console.error("Error setting rundown system preference:", error);
    }
  };

  const handleSendMessage = () => {
    if (!currentMessage.trim() || !api) return;

    const newMessage = {
      id: Date.now().toString(),
      role: "user",
      text: currentMessage,
      timestamp: Date.now(),
      partial: false,
    };

    setMessages((prev) => [...prev, newMessage]);
    api.sendMessage({
      mime_type: 'text/plain',
      data: currentMessage,
    });
    setCurrentMessage("");
  };

  const handleMicToggle = (enabled) => {
    setMicEnabled(enabled);
    if (enabled) {
      initAudio((pcmData) => {
        if (api) {
          api.sendMessage({
            mime_type: 'audio/pcm',
            data: pcmData,
          });
        }
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
          <div className="flex items-center space-x-2">
            <Label htmlFor="rundown-system-toggle">CUEZ</Label>
            <Switch
              id="rundown-system-toggle"
              checked={rundownSystem === "sofie"}
              onCheckedChange={handleRundownChange}
            />
            <Label htmlFor="rundown-system-toggle">SOFIE</Label>
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
      <div className="hidden lg:block w-80 bg-[#1C1A22] border-l border-white/8">
        <TelemetryPanel />
      </div>
    </div>
  );
}