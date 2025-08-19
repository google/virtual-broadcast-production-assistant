
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight } from "lucide-react";
import { format } from "date-fns";

// Mock telemetry data
const mockTelemetry = [
  {
    id: "1",
    turnId: "turn_1",
    type: "function_call",
    name: "get_clip_suggestions", 
    payload: { clipId: "SLUG/CLIPNAME/1826", category: "VIDEO" },
    timestamp: Date.now() - 30000
  },
  {
    id: "2", 
    turnId: "turn_1",
    type: "function_response",
    name: "get_clip_suggestions",
    payload: { suggestions: ["Option A", "Option B", "Option C"], count: 3 },
    timestamp: Date.now() - 29000
  },
  {
    id: "3", 
    turnId: "turn_2",
    type: "function_call",
    name: "a_very_long_function_name_that_should_definitely_overflow_if_not_truncated",
    payload: { query: "What's the weather like in New York today?", unit: "celsius" },
    timestamp: Date.now() - 15000
  },
  {
    id: "4", 
    turnId: "turn_2",
    type: "function_response",
    name: "a_very_long_function_name_that_should_definitely_overflow_if_not_truncated",
    payload: { temperature: "25C", conditions: "Sunny" },
    timestamp: Date.now() - 14000
  }
];

export default function TelemetryPanel() {
  const [expandedEntries, setExpandedEntries] = useState(new Set());

  const toggleExpanded = (id) => {
    const newExpanded = new Set(expandedEntries);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedEntries(newExpanded);
  };

  const groupedByTurn = mockTelemetry.reduce((acc, entry) => {
    if (!acc[entry.turnId]) {
      acc[entry.turnId] = [];
    }
    acc[entry.turnId].push(entry);
    return acc;
  }, {});

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-white/8">
        <h3 className="font-semibold text-[#E6E1E5]">Telemetry</h3>
        <p className="text-xs text-[#A6A0AA] mt-1">Function call trace</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">
        {Object.entries(groupedByTurn).map(([turnId, entries]) => (
          <div key={turnId} className="mb-6">
            <div className="text-xs font-medium text-[#A6A0AA] mb-3 uppercase tracking-wide">
              {turnId}
            </div>
            
            <div className="space-y-2">
              {entries.map((entry) => (
                <div key={entry.id} className="bg-white/5 rounded-lg border border-white/10">
                  <button
                    onClick={() => toggleExpanded(entry.id)}
                    className="w-full p-3 text-left hover:bg-white/5 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0"> {/* Added min-w-0 */}
                        {expandedEntries.has(entry.id) ? (
                          <ChevronDown className="w-4 h-4 text-[#A6A0AA]" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-[#A6A0AA]" />
                        )}
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${
                            entry.type === 'function_call' 
                              ? 'border-[#FF2D86]/30 text-[#FF2D86] bg-[#FF2D86]/10'
                              : 'border-[#14B8A6]/30 text-[#14B8A6] bg-[#14B8A6]/10'
                          }`}
                        >
                          {entry.type === 'function_call' ? 'CALL' : 'RESPONSE'}
                        </Badge>
                        <span className="font-medium text-[#E6E1E5] truncate">{entry.name}</span> {/* Added truncate */}
                      </div>
                      <span className="text-xs text-[#A6A0AA] flex-shrink-0"> {/* Added flex-shrink-0 */}
                        {format(new Date(entry.timestamp), 'HH:mm:ss')}
                      </span>
                    </div>
                  </button>
                  
                  {expandedEntries.has(entry.id) && (
                    <div className="px-3 pb-3">
                      <pre className="text-xs text-[#A6A0AA] bg-black/20 p-3 rounded overflow-x-auto">
                        {JSON.stringify(entry.payload, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
        
        {Object.keys(groupedByTurn).length === 0 && (
          <div className="text-center py-8">
            <p className="text-[#A6A0AA] text-sm">No telemetry data</p>
          </div>
        )}
      </div>
    </div>
  );
}
