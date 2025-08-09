import React from "react";
import IssueCard from "./IssueCard";

const timeSlots = [
  { label: "Now", offset: 0 },
  { label: "+1 min", offset: 60 },
  { label: "+3 min", offset: 180 },  
  { label: "+5 min", offset: 300 },
  { label: "+15 min", offset: 900 }
];

// Mock issues data
const mockIssues = [
  {
    id: "1",
    category: "VIDEO",
    title: "Missing clip", 
    subtitle: "SLUG/CLIPNAME/1826",
    severity: "critical",
    timeOffsetSec: 0,
    status: "default"
  },
  {
    id: "2", 
    category: "AUDIO",
    title: "Distorted audio on clip",
    subtitle: "SLUG/CLIPNAME/1826", 
    severity: "critical",
    timeOffsetSec: 180,
    status: "working"
  },
  {
    id: "3",
    category: "VIDEO", 
    title: "Illegal frames on clip",
    subtitle: "SLUG/CLIPNAME/1826",
    severity: "warning", 
    timeOffsetSec: 300,
    status: "default"
  },
  {
    id: "4",
    category: "REFORMATTING",
    title: "Video aspect ratio mismatch", 
    subtitle: "SLUG/CLIPNAME/1826",
    severity: "warning",
    timeOffsetSec: 300, 
    status: "default"
  },
  {
    id: "5",
    category: "GFX",
    title: "Missing graphic",
    subtitle: "Item 01 - Story strap", 
    severity: "warning",
    timeOffsetSec: 900,
    status: "default"
  }
];

export default function TimelineView() {
  const getIssuesForTimeSlot = (offset) => {
    return mockIssues.filter(issue => issue.timeOffsetSec === offset);
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