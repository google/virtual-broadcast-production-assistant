import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Mic, MicOff, Volume2 } from "lucide-react";

export default function MicControl({ enabled, onToggle }) {
  const [volumeLevel, setVolumeLevel] = useState(0.3); // Mock VU meter

  return (
    <div className="space-y-3">
      {/* Mic Toggle */}
      <Button
        onClick={() => onToggle(!enabled)}
        className={`w-full h-12 font-semibold transition-all duration-200 ${
          enabled
            ? "bg-[#FF2D86] hover:bg-[#FF2D86]/90 text-white"
            : "bg-white/10 hover:bg-white/20 text-[#A6A0AA]"
        }`}
      >
        {enabled ? <Mic className="w-5 h-5 mr-2" /> : <MicOff className="w-5 h-5 mr-2" />}
        {enabled ? "Recording" : "Mic Off"}
      </Button>

      {/* VU Meter */}
      {enabled && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Volume2 className="w-4 h-4 text-[#A6A0AA]" />
            <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-[#14B8A6] to-[#FFC857] transition-all duration-100"
                style={{ width: `${volumeLevel * 100}%` }}
              />
            </div>
          </div>
          <p className="text-xs text-[#A6A0AA]">Hold Space for push-to-talk</p>
        </div>
      )}
    </div>
  );
}