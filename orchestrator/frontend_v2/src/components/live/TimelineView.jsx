import { useState, useEffect } from 'react';
import { collection, query, where, orderBy, onSnapshot } from 'firebase/firestore';
import { db } from '@/lib/firebase';
import { useAuth } from '@/contexts/useAuth';
import IssueCard from "./IssueCard";

const timeSlots = [
  { label: "Now", offset: 0 },
  { label: "+1 min", offset: 60 },
  { label: "+3 min", offset: 180 },  
  { label: "+5 min", offset: 300 },
  { label: "+15 min", offset: 900 }
];

export default function TimelineView() {
  const [issues, setIssues] = useState([]);
  const { currentUser } = useAuth();

  useEffect(() => {
    if (!currentUser) return;

    const q = query(
      collection(db, "timeline_events"),
      where("user_id", "==", currentUser.uid),
      orderBy("timestamp", "desc")
    );

    const unsubscribe = onSnapshot(q, (querySnapshot) => {
      const fetchedIssues = [];
      querySnapshot.forEach((doc) => {
        fetchedIssues.push({ id: doc.id, ...doc.data() });
      });
      setIssues(fetchedIssues);
    });

    // Cleanup subscription on unmount
    return () => unsubscribe();
  }, [currentUser]);

  const getIssuesForTimeSlot = (offset) => {
    // This logic might need adjustment depending on how timeOffsetSec is used.
    // For now, we'll just filter by the offset.
    return issues.filter(issue => issue.timeOffsetSec === offset);
  };

  return (
    <div className="h-full bg-[#0D0B12] p-6">
      <div className="space-y-6">
        {timeSlots.map((slot) => (
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
              {getIssuesForTimeSlot(slot.offset).map((issue) => (
                <IssueCard key={issue.id} issue={issue} />
              ))}
              
              {getIssuesForTimeSlot(slot.offset).length === 0 && (
                <div className="p-6 rounded-xl bg-white/5 border border-white/10 text-center">
                  <p className="text-[#A6A0AA] text-sm">No items</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}