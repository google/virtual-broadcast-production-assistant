import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Search, Users, Filter, Circle } from "lucide-react";

// Mock agents and skills data
const mockAgents = [
  {
    name: "CUEZ Agent",
    description: "Broadcast automation and playlist management",
    status: "online",
    skills: [
      { id: "1", name: "playlist_control", description: "Manage broadcast playlists", tags: ["automation", "scheduling"] },
      { id: "2", name: "graphics_overlay", description: "Control on-screen graphics", tags: ["graphics", "ui"] },
      { id: "3", name: "clip_cuing", description: "Cue and play video clips", tags: ["video", "playback"] }
    ]
  },
  {
    name: "Sofie Agent",
    description: "Studio control and live production",
    status: "online",
    skills: [
      { id: "4", name: "camera_control", description: "Switch between camera angles", tags: ["cameras", "switching"] },
      { id: "5", name: "audio_mixing", description: "Control audio levels and routing", tags: ["audio", "mixing"] },
      { id: "6", name: "lighting_control", description: "Adjust studio lighting", tags: ["lighting", "environment"] }
    ]
  },
  {
    name: "Content Agent",
    description: "Asset management and content discovery",
    status: "busy",
    skills: [
      { id: "7", name: "clip_search", description: "Find and retrieve video clips", tags: ["search", "content"] },
      { id: "8", name: "media_analysis", description: "Analyze media content", tags: ["ai", "analysis"] },
      { id: "9", name: "asset_organization", description: "Organize media assets", tags: ["management", "workflow"] }
    ]
  }
];

export default function Agents() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState(new Set());

  // Get all unique tags
  const allTags = [...new Set(
    mockAgents.flatMap(agent =>
      agent.skills.flatMap(skill => skill.tags || [])
    )
  )];

  const filteredAgents = mockAgents.filter(agent => {
    const matchesSearch = searchQuery === "" ||
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.skills.some(skill =>
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase())
      );

    const matchesTags = selectedTags.size === 0 ||
      agent.skills.some(skill =>
        skill.tags && skill.tags.some(tag => selectedTags.has(tag))
      );

    return matchesSearch && matchesTags;
  });

  const toggleTag = (tag) => {
    const newTags = new Set(selectedTags);
    if (newTags.has(tag)) {
      newTags.delete(tag);
    } else {
      newTags.add(tag);
    }
    setSelectedTags(newTags);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'text-[#14B8A6]';
      case 'busy': return 'text-[#FFC857]';
      case 'offline': return 'text-[#FF2D86]';
      default: return 'text-[#A6A0AA]';
    }
  };

  return (
    <div className="min-h-[calc(100vh-80px)] bg-[#0D0B12] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#E6E1E5] mb-2">AI Agents & Skills</h1>
          <p className="text-[#A6A0AA]">Explore available agents and their capabilities</p>
        </div>

        {/* Search and Filters */}
        <div className="mb-8 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[#A6A0AA]" />
            <Input
              placeholder="Search agents and skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white/5 border-white/10 text-[#E6E1E5] placeholder:text-[#A6A0AA]"
            />
          </div>

          {/* Tag Filter */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-[#A6A0AA]" />
              <span className="text-sm font-medium text-[#E6E1E5]">Filter by skill tags:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {allTags.map((tag) => (
                <Button
                  key={tag}
                  variant="outline"
                  size="sm"
                  onClick={() => toggleTag(tag)}
                  className={`transition-all duration-200 ${
                    selectedTags.has(tag)
                      ? "border-[#FF2D86] text-[#FF2D86] bg-[#FF2D86]/10"
                      : "border-white/20 text-[#A6A0AA] hover:border-white/30"
                  }`}
                >
                  {tag}
                </Button>
              ))}
              {selectedTags.size > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedTags(new Set())}
                  className="text-[#A6A0AA] hover:text-[#E6E1E5]"
                >
                  Clear filters
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Agents Grid */}
        <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
          {filteredAgents.map((agent) => (
            <div key={agent.name} className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl p-6 border border-white/10 hover:border-white/20 transition-all duration-200">
              {/* Agent Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Circle className={`w-3 h-3 fill-current ${getStatusColor(agent.status)}`} />
                    <h3 className="text-xl font-bold text-[#E6E1E5]">{agent.name}</h3>
                  </div>
                  <p className="text-[#A6A0AA] text-sm mb-3">{agent.description}</p>

                  {/* Agent-level tags */}
                  <div className="flex flex-wrap gap-2">
                    {[...new Set(agent.skills.flatMap(skill => skill.tags || []))].slice(0, 3).map(tag => (
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

              {/* Status Badge */}
              <Badge
                variant="outline"
                className={`mb-4 capitalize ${
                  agent.status === 'online'
                    ? 'border-[#14B8A6]/30 text-[#14B8A6] bg-[#14B8A6]/10'
                    : agent.status === 'busy'
                    ? 'border-[#FFC857]/30 text-[#FFC857] bg-[#FFC857]/10'
                    : 'border-[#FF2D86]/30 text-[#FF2D86] bg-[#FF2D86]/10'
                }`}
              >
                {agent.status}
              </Badge>

              {/* Skills */}
              <div className="space-y-3">
                <h4 className="font-semibold text-[#E6E1E5] flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Skills ({agent.skills.length})
                </h4>

                <div className="space-y-2">
                  {agent.skills.map((skill) => (
                    <div key={skill.id} className="p-3 bg-white/5 rounded-lg border border-white/10">
                      <div className="flex items-start justify-between mb-2">
                        <h5 className="font-medium text-[#E6E1E5] text-sm">{skill.name}</h5>
                      </div>
                      <p className="text-xs text-[#A6A0AA] mb-2">{skill.description}</p>

                      <div className="flex flex-wrap gap-1">
                        {skill.tags?.map((tag) => (
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
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredAgents.length === 0 && (
          <div className="text-center py-12">
            <Users className="w-16 h-16 text-[#A6A0AA] mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-[#E6E1E5] mb-2">No agents found</h3>
            <p className="text-[#A6A0AA]">Try adjusting your search or filter criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
