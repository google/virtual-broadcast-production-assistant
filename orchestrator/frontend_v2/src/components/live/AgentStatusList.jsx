
import { useEffect, useState } from "react";
import { collection, onSnapshot } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { Badge } from "@/components/ui/badge";
import { Users, Circle } from "lucide-react";

export default function AgentStatusList() {
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    const agentsCollectionRef = collection(db, "agent_status");

    const unsubscribe = onSnapshot(agentsCollectionRef, (snapshot) => {
      const agentsData = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      setAgents(agentsData);
    });

    // Cleanup listener on component unmount
    return () => unsubscribe();
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'text-[#14B8A6]';
      case 'error': return 'text-[#FFC857]';
      case 'offline': return 'text-[#FF2D86]';
      default: return 'text-[#A6A0AA]';
    }
  };

  const onlineAgentsCount = agents.filter(a => a.status === 'online').length;

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-4 h-4 text-[#A6A0AA]" />
        <h3 className="font-semibold text-[#E6E1E5]">Agents</h3>
        <Badge variant="outline" className="text-xs text-[#A6A0AA]">
          {onlineAgentsCount} online
        </Badge>
      </div>
      
      <div className="space-y-3">
        {agents.map((agent) => (
          <div key={agent.id} className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Circle className={`w-2 h-2 fill-current ${getStatusColor(agent.status)}`} />
                  <h4 className="font-medium text-[#E6E1E5] text-sm">{agent.name}</h4>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {agent.tags && agent.tags.map((tag) => (
                    <Badge
                      key={tag}
                      variant="outline"
                      className="text-xs text-[#A6A0AA] border-white/20"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
