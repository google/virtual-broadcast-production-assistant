
import { Badge } from "@/components/ui/badge";
import { Users, Circle } from "lucide-react";

// Mock agents data
const mockAgents = [
  { name: "CUEZ Agent", description: "Broadcast automation", status: "online", skills: ["playlist", "graphics"] },
  { name: "Sofie Agent", description: "Studio control", status: "online", skills: ["cameras", "audio"] },
  { name: "Content Agent", description: "Asset management", status: "busy", skills: ["clips", "media"] }
];

export default function AgentStatusList() {
  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'text-[#14B8A6]';
      case 'busy': return 'text-[#FFC857]'; 
      case 'offline': return 'text-[#FF2D86]';
      default: return 'text-[#A6A0AA]';
    }
  };

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-4 h-4 text-[#A6A0AA]" />
        <h3 className="font-semibold text-[#E6E1E5]">Agents</h3>
        <Badge variant="outline" className="text-xs text-[#A6A0AA]">
          {mockAgents.filter(a => a.status === 'online').length} online
        </Badge>
      </div>
      
      <div className="space-y-3">
        {mockAgents.map((agent) => (
          <div key={agent.name} className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Circle className={`w-2 h-2 fill-current ${getStatusColor(agent.status)}`} />
                  <h4 className="font-medium text-[#E6E1E5] text-sm">{agent.name}</h4>
                </div>
                <p className="text-xs text-[#A6A0AA]">{agent.description}</p>
              </div>
            </div>
            
            <div className="flex gap-1 flex-wrap">
              {agent.skills.map((skill) => (
                <Badge key={skill} variant="outline" className="text-xs text-[#A6A0AA] border-white/20">
                  {skill}
                </Badge>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}