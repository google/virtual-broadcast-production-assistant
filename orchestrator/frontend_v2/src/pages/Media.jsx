import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Play, Plus, RefreshCw, X, Volume2, VolumeX } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

// Mock media suggestions
const mockMediaSuggestions = [
  {
    id: "A",
    label: "Option A",
    title: "Economic Summit Opening", 
    description: "Wide shot of conference hall with delegates arriving",
    duration: "0:45",
    thumbnail: "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=400&h=225&fit=crop",
    type: "video"
  },
  {
    id: "B", 
    label: "Option B",
    title: "Prime Minister Statement",
    description: "Close-up shot during press conference", 
    duration: "1:12",
    thumbnail: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=225&fit=crop",
    type: "video"
  },
  {
    id: "C",
    label: "Option C", 
    title: "Financial District Aerial",
    description: "Drone footage of business district skyline",
    duration: "0:30",
    thumbnail: "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=400&h=225&fit=crop", 
    type: "video"
  },
  {
    id: "D",
    label: "Option D",
    title: "Breaking News Graphic",
    description: "Lower third with urgent styling",
    duration: "0:05", 
    thumbnail: "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=400&h=225&fit=crop",
    type: "graphic"
  }
];

export default function Media() {
  const [suggestions, setSuggestions] = useState(mockMediaSuggestions);
  const [previewMedia, setPreviewMedia] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);

  const handleRefreshSuggestions = async () => {
    setIsRefreshing(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Shuffle suggestions as mock refresh
    const shuffled = [...suggestions].sort(() => Math.random() - 0.5);
    setSuggestions(shuffled);
    setIsRefreshing(false);
  };

  const handleAddNewSuggestion = () => {
    const newSuggestion = {
      id: String.fromCharCode(65 + suggestions.length), // Next letter
      label: `Option ${String.fromCharCode(65 + suggestions.length)}`,
      title: "Custom Content",
      description: "User added media suggestion",
      duration: "0:00",
      thumbnail: "https://images.unsplash.com/photo-1611224923853-80b023f02d71?w=400&h=225&fit=crop",
      type: "video"
    };
    setSuggestions(prev => [...prev, newSuggestion]);
  };

  return (
    <div className="min-h-[calc(100vh-80px)] bg-[#0D0B12] p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#E6E1E5] mb-2">Media Suggestions & Preview</h1>
            <p className="text-[#A6A0AA]">AI-curated content options for your broadcast</p>
          </div>
          
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={handleRefreshSuggestions}
              disabled={isRefreshing}
              className="gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              {isRefreshing ? 'Refreshing...' : 'Refresh Suggestions'}
            </Button>
          </div>
        </div>

        {/* Media Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
          {suggestions.map((media) => (
            <div key={media.id} className="group relative bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl overflow-hidden border border-white/10 hover:border-white/20 transition-all duration-200">
              {/* Thumbnail */}
              <div className="relative aspect-video bg-black overflow-hidden">
                <img 
                  src={media.thumbnail} 
                  alt={media.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                />
                
                {/* Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                
                {/* Play Button */}
                <button
                  onClick={() => setPreviewMedia(media)}
                  className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                >
                  <div className="w-16 h-16 bg-[#FF2D86] rounded-full flex items-center justify-center hover:bg-[#FF2D86]/90 transition-colors">
                    <Play className="w-6 h-6 text-white ml-1" fill="currentColor" />
                  </div>
                </button>
                
                {/* Duration */}
                <div className="absolute bottom-2 right-2">
                  <Badge className="bg-black/60 text-white border-none">
                    {media.duration}
                  </Badge>
                </div>
                
                {/* Type Badge */}
                <div className="absolute top-2 left-2">
                  <Badge 
                    variant="outline"
                    className={
                      media.type === 'video'
                        ? 'border-[#FF2D86]/30 text-[#FF2D86] bg-[#FF2D86]/10'
                        : 'border-[#FFC857]/30 text-[#FFC857] bg-[#FFC857]/10'
                    }
                  >
                    {media.type.toUpperCase()}
                  </Badge>
                </div>
              </div>

              {/* Content */}
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <Badge 
                    variant="outline" 
                    className="bg-[#14B8A6]/10 text-[#14B8A6] border-[#14B8A6]/30 font-bold"
                  >
                    {media.label}
                  </Badge>
                </div>
                
                <h3 className="font-semibold text-[#E6E1E5] mb-1 line-clamp-1">{media.title}</h3>
                <p className="text-sm text-[#A6A0AA] line-clamp-2 mb-4">{media.description}</p>
                
                <Button 
                  className="w-full bg-[#FF2D86] hover:bg-[#FF2D86]/90"
                  onClick={() => {/* Handle add to timeline */}}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add to Timeline
                </Button>
              </div>
            </div>
          ))}

          {/* Add New Card */}
          <button
            onClick={handleAddNewSuggestion}
            className="group relative bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl border-2 border-dashed border-white/20 hover:border-[#FF2D86]/50 transition-all duration-200 p-8 flex flex-col items-center justify-center min-h-[280px]"
          >
            <div className="w-16 h-16 bg-[#FF2D86]/20 rounded-full flex items-center justify-center mb-4 group-hover:bg-[#FF2D86]/30 transition-colors">
              <Plus className="w-8 h-8 text-[#FF2D86]" />
            </div>
            <h3 className="font-semibold text-[#E6E1E5] mb-2">Add Custom</h3>
            <p className="text-sm text-[#A6A0AA] text-center">Upload or select additional content</p>
          </button>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            { label: "Total Suggestions", value: suggestions.length },
            { label: "Video Content", value: suggestions.filter(s => s.type === 'video').length },
            { label: "Graphics", value: suggestions.filter(s => s.type === 'graphic').length },
            { label: "Last Updated", value: "2 min ago" }
          ].map((stat) => (
            <div key={stat.label} className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl p-4 border border-white/10">
              <p className="text-[#A6A0AA] text-sm">{stat.label}</p>
              <p className="text-xl font-bold text-[#E6E1E5]">{stat.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Preview Modal */}
      <Dialog open={!!previewMedia} onOpenChange={() => setPreviewMedia(null)}>
        <DialogContent className="max-w-4xl bg-[#1C1A22] border-white/10">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between text-[#E6E1E5]">
              <span>Media Preview - {previewMedia?.label}</span>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setAudioEnabled(!audioEnabled)}
                  className="text-[#A6A0AA] hover:text-[#E6E1E5]"
                >
                  {audioEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPreviewMedia(null)}
                  className="text-[#A6A0AA] hover:text-[#E6E1E5]"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </DialogTitle>
          </DialogHeader>
          
          {previewMedia && (
            <div className="space-y-4">
              {/* Video Preview */}
              <div className="aspect-video bg-black rounded-lg overflow-hidden">
                <img 
                  src={previewMedia.thumbnail}
                  alt={previewMedia.title}
                  className="w-full h-full object-cover"
                />
              </div>
              
              {/* Media Info */}
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-[#E6E1E5] mb-2">{previewMedia.title}</h3>
                  <p className="text-[#A6A0AA] mb-4">{previewMedia.description}</p>
                  
                  <div className="flex items-center gap-4">
                    <Badge className="bg-[#14B8A6]/10 text-[#14B8A6] border-[#14B8A6]/30">
                      Duration: {previewMedia.duration}
                    </Badge>
                    <Badge 
                      className={
                        previewMedia.type === 'video'
                          ? 'bg-[#FF2D86]/10 text-[#FF2D86] border-[#FF2D86]/30'
                          : 'bg-[#FFC857]/10 text-[#FFC857] border-[#FFC857]/30'
                      }
                    >
                      {previewMedia.type.toUpperCase()}
                    </Badge>
                  </div>
                </div>
                
                <Button className="bg-[#FF2D86] hover:bg-[#FF2D86]/90">
                  <Plus className="w-4 h-4 mr-2" />
                  Add to Timeline
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}