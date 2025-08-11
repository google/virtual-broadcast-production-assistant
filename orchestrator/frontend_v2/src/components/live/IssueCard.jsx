import React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MoreHorizontal, Loader2 } from "lucide-react";

const categoryColors = {
  VIDEO: "bg-[#FF2D86]/20 text-[#FF2D86] border-[#FF2D86]/30",
  AUDIO: "bg-[#FF2D86]/20 text-[#FF2D86] border-[#FF2D86]/30", 
  GFX: "bg-[#FFC857]/20 text-[#FFC857] border-[#FFC857]/30",
  CHECKS: "bg-[#14B8A6]/20 text-[#14B8A6] border-[#14B8A6]/30",
  REFORMATTING: "bg-[#FFC857]/20 text-[#FFC857] border-[#FFC857]/30"
};

const severityColors = {
  critical: { primary: "bg-[#FF2D86] hover:bg-[#FF2D86]/90", secondary: "text-[#FF2D86] hover:bg-[#FF2D86]/10" },
  warning: { primary: "bg-[#FFC857] hover:bg-[#FFC857]/90 text-black", secondary: "text-[#FFC857] hover:bg-[#FFC857]/10" },
  info: { primary: "bg-[#14B8A6] hover:bg-[#14B8A6]/90", secondary: "text-[#14B8A6] hover:bg-[#14B8A6]/10" }
};

const actionLabels = {
  VIDEO: { primary: "Find suggestions", secondary: "Dismiss" },
  AUDIO: { primary: "Skip item", secondary: "Dismiss" }, 
  GFX: { primary: "Generate suggestions", secondary: "Dismiss" },
  CHECKS: { primary: "Try fix", secondary: "Dismiss" },
  REFORMATTING: { primary: "Re-format clip", secondary: "Dismiss" }
};

export default function IssueCard({ issue }) {
  const categoryColorClass = categoryColors[issue.category] || categoryColors.CHECKS;
  const severityColor = severityColors[issue.severity] || severityColors.info;
  const actions = actionLabels[issue.category] || actionLabels.CHECKS;

  return (
    <div className={`relative overflow-hidden rounded-xl bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border ${
      issue.status === 'working' ? 'border-[#FFC857]/50' : 'border-white/10'
    }`}>
      {/* Subtle glow effect for active items */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-50" />
      
      <div className="relative p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <Badge variant="outline" className={`text-xs uppercase font-bold ${categoryColorClass}`}>
              {issue.category}
            </Badge>
            <span className="text-xs text-[#A6A0AA]">just now</span>
          </div>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            <MoreHorizontal className="w-3 h-3" />
          </Button>
        </div>

        {/* Content */}
        <div className="mb-4">
          <h4 className="font-semibold text-[#E6E1E5] mb-1">{issue.title}</h4>
          {issue.subtitle && (
            <p className="text-sm text-[#A6A0AA]">{issue.subtitle}</p>
          )}
        </div>

        {/* Working State */}
        {issue.status === 'working' && (
          <div className="flex items-center justify-center mb-4 py-4">
            <Loader2 className="w-6 h-6 animate-spin text-[#FFC857]" />
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button 
            className={`flex-1 font-medium ${severityColor.primary}`}
            disabled={issue.status === 'working'}
          >
            {actions.primary}
          </Button>
          <Button 
            variant="outline"
            className={severityColor.secondary}
            disabled={issue.status === 'working'}
          >
            {actions.secondary}
          </Button>
        </div>
      </div>
    </div>
  );
}