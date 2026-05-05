import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight } from "lucide-react";
import { format } from "date-fns";
import { useAuth } from "@/contexts/useAuth";
import { db } from "@/lib/firebase";
import { collection, query, where, onSnapshot, orderBy } from "firebase/firestore";

export default function TelemetryPanel() {
  const [expandedEntries, setExpandedEntries] = useState(new Set());
  const [telemetry, setTelemetry] = useState([]);
  const { currentUser } = useAuth();

  useEffect(() => {
    if (!currentUser) return;

    const chatSessionRef = collection(db, "chat_sessions", currentUser.uid, "events");
    const q = query(
      chatSessionRef,
      where("type", "in", ["TOOL_START", "TOOL_END"]),
      orderBy("timestamp", "desc")
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const newTelemetry = snapshot.docs.map((doc) => ({
        id: doc.id,
        ...doc.data(),
      }));
      setTelemetry(newTelemetry);
    });

    return () => unsubscribe();
  }, [currentUser]);

  const toggleExpanded = (id) => {
    const newExpanded = new Set(expandedEntries);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedEntries(newExpanded);
  };

  const groupedByTurn = telemetry.reduce((acc, entry) => {
    const turnId = entry.turn_id || `turn_${entry.timestamp.toMillis()}`;
    if (!acc[turnId]) {
      acc[turnId] = [];
    }
    acc[turnId].push(entry);
    return acc;
  }, {});

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-white/8">
        <h3 className="font-semibold text-[#E6E1E5]">Telemetry</h3>
        <p className="text-xs text-[#A6A0AA] mt-1">Tool call trace</p>
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
                      <div className="flex items-center gap-2 min-w-0">
                        {expandedEntries.has(entry.id) ? (
                          <ChevronDown className="w-4 h-4 text-[#A6A0AA]" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-[#A6A0AA]" />
                        )}
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            entry.type === 'TOOL_START'
                              ? 'border-[#FF2D86]/30 text-[#FF2D86] bg-[#FF2D86]/10'
                              : 'border-[#14B8A6]/30 text-[#14B8A6] bg-[#14B8A6]/10'
                          }`}
                        >
                          {entry.type === 'TOOL_START' ? 'START' : 'END'}
                        </Badge>
                        <span className="font-medium text-[#E6E1E5] truncate">{entry.tool_name}</span>
                      </div>
                      <span className="text-xs text-[#A6A0AA] flex-shrink-0">
                        {entry.timestamp && format(entry.timestamp.toDate(), 'HH:mm:ss')}
                      </span>
                    </div>
                  </button>

                  {expandedEntries.has(entry.id) && (
                    <div className="px-3 pb-3">
                      <pre className="text-xs text-[#A6A0AA] bg-black/20 p-3 rounded overflow-x-auto">
                        {JSON.stringify(entry.type === 'TOOL_START' ? entry.tool_args : entry.tool_output, null, 2)}
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
