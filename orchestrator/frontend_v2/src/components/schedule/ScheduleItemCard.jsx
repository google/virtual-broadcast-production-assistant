
import { Badge } from '@/components/ui/badge';

const categoryColors = {
  VIDEO: "bg-[#FF2D86]/20 text-[#FF2D86] border-[#FF2D86]/30",
  AUDIO: "bg-[#FF2D86]/20 text-[#FF2D86] border-[#FF2D86]/30",
  GFX: "bg-[#FFC857]/20 text-[#FFC857] border-[#FFC857]/30",
  CHECKS: "bg-[#14B8A6]/20 text-[#14B8A6] border-[#14B8A6]/30",
};

export default function ScheduleItemCard({ item, isSelected, onSelect }) {
  const categoryColorClass = categoryColors[item.category] || categoryColors.CHECKS;

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left relative overflow-hidden rounded-xl bg-gradient-to-br from-[#1C1A22] to-[#2A2731] border transition-all duration-200
        ${isSelected ? 'border-[#FF2D86]/80 ring-2 ring-[#FF2D86]/50' : 'border-white/10 hover:border-white/20'}`}
    >
      <div className="relative p-4">
        <div className="flex items-start justify-between mb-2">
          <Badge variant="outline" className={`text-xs uppercase font-bold ${categoryColorClass}`}>
            {item.category}
          </Badge>
          <div className="flex items-center gap-2">
            {item.skipped && (
              <Badge variant="destructive" className="h-5 px-2 text-xs">Skipped</Badge>
            )}
            <span className="text-xs text-[#A6A0AA]">{item.durationSec}s</span>
          </div>
        </div>
        <div>
          <h4 className={`font-semibold text-[#E6E1E5] ${item.skipped ? 'line-through text-[#A6A0AA]' : ''}`}>
            {item.title}
          </h4>
          {item.slug && (
            <p className="text-sm text-[#A6A0AA]">{item.slug}</p>
          )}
        </div>
      </div>
    </button>
  );
}