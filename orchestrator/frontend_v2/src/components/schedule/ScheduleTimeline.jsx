import React, { useRef, useEffect } from 'react';
import ScheduleItemCard from './ScheduleItemCard';

const timeSlots = [
  { label: "Now", offset: 0 },
  { label: "+1 min", offset: 60 },
  { label: "+3 min", offset: 180 },
  { label: "+5 min", offset: 300 },
  { label: "+15 min", offset: 900 }
];

export default function ScheduleTimeline({ episode, selectedItemId, onSelectItem }) {
  const allItems = episode.parts.flatMap(part => part.items);
  const itemRefs = useRef({});

  useEffect(() => {
    if (selectedItemId && itemRefs.current[selectedItemId]) {
      itemRefs.current[selectedItemId].scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [selectedItemId]);

  const getItemsForTimeSlot = (startTime, endTime) => {
    let cumulativeTime = 0;
    const itemsInSlot = [];

    for (const item of allItems) {
      if (item.skipped) continue;
      
      const itemStartTime = cumulativeTime;
      const itemEndTime = cumulativeTime + (item.durationSec || 0);

      if (itemEndTime > startTime && itemStartTime < endTime) {
        itemsInSlot.push(item);
      }
      cumulativeTime = itemEndTime;
      if (cumulativeTime >= endTime) break;
    }
    return itemsInSlot;
  };

  const getTimeSlotItems = () => {
    return timeSlots.map((slot, index) => {
      const nextSlot = timeSlots[index + 1];
      const startTime = slot.offset;
      const endTime = nextSlot ? nextSlot.offset : Infinity;
      return {
        ...slot,
        items: getItemsForTimeSlot(startTime, endTime),
      };
    });
  };

  return (
    <div className="h-full bg-[#0D0B12] p-6">
      <div className="space-y-6">
        {getTimeSlotItems().map((slot) => (
          <div key={slot.label} className="space-y-3">
            <div className="flex items-center gap-4">
              <h3 className="text-lg font-semibold text-[#E6E1E5] min-w-[80px]">
                {slot.label}
              </h3>
              <div className="flex-1 h-px bg-white/10" />
            </div>
            <div className="grid gap-3">
              {slot.items.length > 0 ? (
                slot.items.map((item) => (
                  <div key={item.id} ref={el => itemRefs.current[item.id] = el}>
                    <ScheduleItemCard 
                        item={item} 
                        isSelected={selectedItemId === item.id}
                        onSelect={() => onSelectItem(item.id)}
                    />
                  </div>
                ))
              ) : (
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