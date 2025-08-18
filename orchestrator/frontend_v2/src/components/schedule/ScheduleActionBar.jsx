
import { Button } from '@/components/ui/button';
import { Undo, Redo, Save, XCircle, AlertCircle } from 'lucide-react';

export default function ScheduleActionBar({
  onApply,
  onDiscard,
  onUndo,
  onRedo,
  hasChanges,
  canUndo,
  canRedo,
  isPending,
  error,
}) {
  return (
    <div className="sticky top-0 bg-[#1C1A22] border-b border-white/8 z-10 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            onClick={onApply}
            disabled={!hasChanges || isPending}
            className="bg-[#FF2D86] hover:bg-[#FF2D86]/90 font-semibold gap-2"
          >
            <Save className="w-4 h-4" />
            {isPending ? 'Applying...' : 'Apply Changes'}
          </Button>
          <Button
            variant="outline"
            onClick={onDiscard}
            disabled={!hasChanges || isPending}
            className="gap-2"
          >
            <XCircle className="w-4 h-4" />
            Discard
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={onUndo} disabled={!canUndo || isPending}>
            <Undo className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onRedo} disabled={!canRedo || isPending}>
            <Redo className="w-4 h-4" />
          </Button>
        </div>
      </div>
      {error && (
        <div className="mt-2 text-sm text-[#FF2D86] flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>Error: {error}</span>
        </div>
      )}
    </div>
  );
}