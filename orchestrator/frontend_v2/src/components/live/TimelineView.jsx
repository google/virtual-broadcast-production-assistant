import { useState, useEffect } from 'react';
import IssueCard from "./IssueCard";

// Time slots are defined by their boundaries in seconds relative to the current time.
// A positive offset is the future, a negative offset is the past.
const timeSlots = [
  { label: "Upcoming", min: 60, max: Infinity },
  { label: "Now", min: -60, max: 60 },
  { label: "Recently", min: -300, max: -60 }, // 1 to 5 minutes ago
  { label: "5 minutes ago", min: -900, max: -300 }, // 5 to 15 minutes ago
];

export default function TimelineView({ issues }) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
        setNow(new Date());
    }, 5000); // Update every 5 seconds

    // Cleanup subscription on unmount
    return () => {
        clearInterval(interval);
    }
  }, []);

  const getIssuesForTimeSlot = (slot) => {
    return issues.filter(issue => {
        if (!issue.timestamp) return false;

        const issueCreationTime = issue.timestamp.toDate().getTime();
        const issueIntendedTime = issueCreationTime + ((issue.timeOffsetSec || 0) * 1000);
        
        const timeDiffSec = (issueIntendedTime - now.getTime()) / 1000;

        // Check if the issue's time difference falls into this slot's bucket.
        return timeDiffSec < slot.max && timeDiffSec >= slot.min;
    });
  };

  return (
    <div className="h-full bg-[#0D0B12] p-6">
      <div className="space-y-6">
        {timeSlots.map((slot) => {
          const issuesForSlot = getIssuesForTimeSlot(slot);
          return (
            <div key={slot.label} className="space-y-3">
              {/* Time Label */}
              <div className="flex items-center gap-4">
                <h3 className="text-lg font-semibold text-[#E6E1E5] min-w-[80px]">
                  {slot.label}
                </h3>
                <div className="flex-1 h-px bg-white/10" />
              </div>

              {/* Issues for this time slot */}
              <div className="grid gap-3">
                {issuesForSlot.map((issue) => (
                  <IssueCard key={issue.id} issue={issue} />
                ))}
                
                {issuesForSlot.length === 0 && (
                  <div className="p-6 rounded-xl bg-white/5 border border-white/10 text-center">
                    <p className="text-[#A6A0AA] text-sm">No items</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}