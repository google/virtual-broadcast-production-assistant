import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MoreHorizontal, Loader2, PenLine, CheckCircle, PlayCircle } from "lucide-react";
import { sendMessage } from "@/api/webSocket";
import { db } from "@/lib/firebase";
import { doc, updateDoc } from "firebase/firestore";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const categoryColors = {
  VIDEO: "bg-[#FF2D86]/20 text-[#FF2D86] border-[#FF2D86]/30",
  AUDIO: "bg-[#FF2D86]/20 text-[#FF2D86] border-[#FF2D86]/30",
  GFX: "bg-[#FFC857]/20 text-[#FFC857] border-[#FFC857]/30",
  CHECKS: "bg-[#14B8A6]/20 text-[#14B8A6] border-[#14B8A6]/30",
  REFORMATTING: "bg-[#FFC857]/20 text-[#FFC857] border-[#FFC857]/30",
  QC: "bg-blue-500/20 text-blue-400 border-blue-400/30",
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
  const [isPlayerOpen, setIsPlayerOpen] = useState(false);
  const categoryColorClass = categoryColors[issue.category] || categoryColors.CHECKS;
  const severityColor = severityColors[issue.severity] || severityColors.info;
  const actions = actionLabels[issue.category] || actionLabels.CHECKS;
  console.log(issue);
  const handleCorrect = async () => {
    const prompt = `Please correct the spelling of '${issue.details.original_word}' to '${issue.details.suggested_correction}' in the content identified by UID ${issue.details.context_uid}.`;
    sendMessage({
      mime_type: 'text/plain',
      data: prompt,
    });
    const issueRef = doc(db, "timeline_events", issue.id);
    await updateDoc(issueRef, { status: "working" });
    toast.info("Sent correction request to the agent.");
  };

  const handleDismiss = async () => {
    const issueRef = doc(db, "timeline_events", issue.id);
    await updateDoc(issueRef, { status: "dismissed" });
    toast.success("Issue dismissed.");
  };

  if (issue.type === 'VIDEO_CLIP') {
    const thumbnailUrl = issue.details?.thumbnail_uri || 'https://placehold.co/600x400?text=Video+Preview';
    const videoUrl = (issue.details?.tc_in && issue.details?.tc_out)
      ? `${issue.details.video_uri}#t=${issue.details.tc_in},${issue.details.tc_out}`
      : issue.details?.video_uri;

    return (
      <>
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border border-white/10">
          <div className="relative group aspect-video">
            <img src={thumbnailUrl} alt={issue.title} className="w-full h-full object-cover" />
            <div
              className="absolute inset-0 bg-black/40 flex items-center justify-center cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => setIsPlayerOpen(true)}
            >
              <PlayCircle className="w-16 h-16 text-white/80 hover:text-white transition-colors" />
            </div>
          </div>
          <div className="p-4">
            <h4 className="font-semibold text-[#E6E1E5] mb-1 truncate">{issue.title}</h4>
            <p className="text-sm text-[#A6A0AA] truncate">{issue.subtitle}</p>
          </div>
        </div>

        <Dialog open={isPlayerOpen} onOpenChange={setIsPlayerOpen}>
          <DialogContent className="max-w-4xl w-[90vw] bg-[#0D0B12] border-white/10 text-white">
            <DialogHeader>
              <DialogTitle>{issue.title}</DialogTitle>
            </DialogHeader>
            <video controls autoPlay src={videoUrl} className="w-full rounded-lg aspect-video">
              Your browser does not support the video tag.
            </video>
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <div className={cn(
      'relative overflow-hidden rounded-xl bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border',
      {
        'border-[#FFC857]/50': issue.status === 'working',
        'border-white/10': issue.status !== 'working',
        'opacity-60 grayscale-[50%]': issue.status === 'corrected',
      }
    )}>
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-50" />

      <div className="relative p-4">
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

        <div className="mb-4">
          <h4 className="font-semibold text-[#E6E1E5] mb-1">{issue.title}</h4>
          {issue.subtitle && (
            <p className="text-sm text-[#A6A0AA]">{issue.subtitle}</p>
          )}
          {issue.type === 'SPELLING_ERROR' && issue.details && (
            <div className="mt-3 text-sm bg-black/20 p-3 rounded-md">
              <div className="flex items-center gap-2">
                <span className="text-red-400 line-through">{issue.details.original_word}</span>
                <span>→</span>
                <span className="text-green-400">{issue.details.suggested_correction}</span>
              </div>
              <p className="text-xs text-[#A6A0AA] mt-1">UID: {issue.details.context_uid}</p>
            </div>
          )}
        </div>

        {issue.status === 'working' && (
          <div className="flex items-center justify-center mb-4 py-4">
            <Loader2 className="w-6 h-6 animate-spin text-[#FFC857]" />
          </div>
        )}

        {issue.status === 'corrected' ? (
          <div className="flex items-center justify-center h-10">
            <CheckCircle className="w-5 h-5 text-green-400 mr-2" />
            <span className="font-medium text-green-400">Corrected</span>
          </div>
        ) : (
          <div className="flex gap-2">
            {issue.type === 'SPELLING_ERROR' ? (
              <>
                <Button
                  className={`flex-1 font-medium ${severityColor.primary}`}
                  disabled={issue.status === 'working'}
                  onClick={handleCorrect}
                >
                  <PenLine className="w-4 h-4 mr-2" />
                  Correct
                </Button>
                <Button
                  variant="outline"
                  className={severityColor.secondary}
                  disabled={issue.status === 'working'}
                  onClick={handleDismiss}
                >
                  Dismiss
                </Button>
              </>
            ) : (
              <>
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
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
