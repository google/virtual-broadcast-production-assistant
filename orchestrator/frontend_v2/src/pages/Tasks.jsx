
import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight, Clock, CheckCircle, XCircle, Loader2, ClipboardList } from "lucide-react";
import { format } from "date-fns";

// Mock task data
const mockTasks = [
  {
    id: "1",
    turnId: "turn_1",
    timestamp: Date.now() - 180000, // 3 minutes ago
    status: "completed",
    calls: [
      {
        id: "call_1",
        type: "function_call", 
        name: "find_clip_suggestions",
        payload: { clipId: "SLUG/CLIPNAME/1826", category: "VIDEO" },
        timestamp: Date.now() - 180000
      },
      {
        id: "response_1",
        type: "function_response",
        name: "find_clip_suggestions", 
        payload: { suggestions: ["Option A", "Option B", "Option C"], count: 3 },
        timestamp: Date.now() - 179000
      }
    ]
  },
  {
    id: "2", 
    turnId: "turn_2",
    timestamp: Date.now() - 120000, // 2 minutes ago
    status: "working",
    calls: [
      {
        id: "call_2",
        type: "function_call",
        name: "generate_graphics",
        payload: { type: "lower_third", text: "Breaking News", style: "urgent" },
        timestamp: Date.now() - 120000
      }
    ]
  },
  {
    id: "3",
    turnId: "turn_3", 
    timestamp: Date.now() - 60000, // 1 minute ago
    status: "failed",
    calls: [
      {
        id: "call_3",
        type: "function_call",
        name: "audio_level_check",
        payload: { channel: "mic_1", target_level: -12 },
        timestamp: Date.now() - 60000
      },
      {
        id: "response_3",
        type: "function_response", 
        name: "audio_level_check",
        payload: { error: "Channel not found", code: "CHANNEL_NOT_FOUND" },
        timestamp: Date.now() - 59000
      }
    ]
  }
];

export default function Tasks() {
  const [expandedTasks, setExpandedTasks] = useState(new Set());

  const toggleExpanded = (taskId) => {
    const newExpanded = new Set(expandedTasks);
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId);
    } else {
      newExpanded.add(taskId);
    }
    setExpandedTasks(newExpanded);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-[#14B8A6]" />;
      case 'working':
        return <Loader2 className="w-4 h-4 text-[#FFC857] animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-[#FF2D86]" />;
      default:
        return <Clock className="w-4 h-4 text-[#A6A0AA]" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'border-[#14B8A6]/30 text-[#14B8A6] bg-[#14B8A6]/10';
      case 'working':
        return 'border-[#FFC857]/30 text-[#FFC857] bg-[#FFC857]/10';
      case 'failed':
        return 'border-[#FF2D86]/30 text-[#FF2D86] bg-[#FF2D86]/10';
      default:
        return 'border-white/30 text-[#A6A0AA] bg-white/5';
    }
  };

  return (
    <div className="min-h-[calc(100vh-80px)] bg-[#0D0B12] p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#E6E1E5] mb-2">Task Log & History</h1>
          <p className="text-[#A6A0AA]">Complete audit trail of agent interactions grouped by conversation turn</p>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total Tasks", value: mockTasks.length, color: "text-[#E6E1E5]" },
            { label: "Completed", value: mockTasks.filter(t => t.status === 'completed').length, color: "text-[#14B8A6]" },
            { label: "Working", value: mockTasks.filter(t => t.status === 'working').length, color: "text-[#FFC857]" },
            { label: "Failed", value: mockTasks.filter(t => t.status === 'failed').length, color: "text-[#FF2D86]" }
          ].map((stat) => (
            <div key={stat.label} className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl p-4 border border-white/10">
              <p className="text-[#A6A0AA] text-sm">{stat.label}</p>
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Task List */}
        <div className="space-y-4">
          {mockTasks.map((task) => (
            <div key={task.id} className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl border border-white/10 overflow-hidden">
              {/* Task Header */}
              <button
                onClick={() => toggleExpanded(task.id)}
                className="w-full p-6 text-left hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {expandedTasks.has(task.id) ? (
                      <ChevronDown className="w-5 h-5 text-[#A6A0AA]" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-[#A6A0AA]" />
                    )}
                    
                    {getStatusIcon(task.status)}
                    
                    <div>
                      <h3 className="font-semibold text-[#E6E1E5]">{task.turnId}</h3>
                      <p className="text-sm text-[#A6A0AA]">
                        {task.calls.length} function call{task.calls.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className={getStatusColor(task.status)}>
                      {task.status}
                    </Badge>
                    <span className="text-sm text-[#A6A0AA]">
                      {format(new Date(task.timestamp), 'HH:mm:ss')}
                    </span>
                  </div>
                </div>
              </button>

              {/* Expanded Content */}
              {expandedTasks.has(task.id) && (
                <div className="border-t border-white/10 p-6 pt-0">
                  <div className="space-y-4 mt-6">
                    {task.calls.map((call, index) => (
                      <div key={call.id} className="relative">
                        {/* Timeline line */}
                        {index < task.calls.length - 1 && (
                          <div className="absolute left-6 top-8 w-px h-8 bg-white/20" />
                        )}
                        
                        <div className="flex gap-4">
                          <div className="flex-shrink-0">
                            <div className={`w-3 h-3 rounded-full ${
                              call.type === 'function_call' 
                                ? 'bg-[#FF2D86]' 
                                : 'bg-[#14B8A6]'
                            }`} />
                          </div>
                          
                          <div className="flex-1 bg-white/5 rounded-lg p-4 border border-white/10">
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-3">
                                <Badge 
                                  variant="outline"
                                  className={`text-xs ${
                                    call.type === 'function_call'
                                      ? 'border-[#FF2D86]/30 text-[#FF2D86] bg-[#FF2D86]/10'
                                      : 'border-[#14B8A6]/30 text-[#14B8A6] bg-[#14B8A6]/10'
                                  }`}
                                >
                                  {call.type === 'function_call' ? 'CALL' : 'RESPONSE'}
                                </Badge>
                                <span className="font-medium text-[#E6E1E5]">{call.name}</span>
                              </div>
                              <span className="text-xs text-[#A6A0AA]">
                                {format(new Date(call.timestamp), 'HH:mm:ss.SSS')}
                              </span>
                            </div>
                            
                            <pre className="text-xs text-[#A6A0AA] bg-black/20 p-3 rounded overflow-x-auto">
                              {JSON.stringify(call.payload, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {mockTasks.length === 0 && (
          <div className="text-center py-12">
            <ClipboardList className="w-16 h-16 text-[#A6A0AA] mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-[#E6E1E5] mb-2">No tasks yet</h3>
            <p className="text-[#A6A0AA]">Task history will appear here as agents process requests</p>
          </div>
        )}
      </div>
    </div>
  );
}
