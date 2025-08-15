import React from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { GripVertical, MoreHorizontal } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

const ItemContextMenu = ({ onSkip, onUnskip, isSkipped }) => (
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button variant="ghost" size="icon" className="h-6 w-6">
        <MoreHorizontal className="w-4 h-4" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent>
      {isSkipped ? (
        <DropdownMenuItem onClick={onUnskip}>Un-skip Item</DropdownMenuItem>
      ) : (
        <DropdownMenuItem onClick={onSkip}>Skip Item</DropdownMenuItem>
      )}
      <DropdownMenuItem>Insert Placeholder After</DropdownMenuItem>
      <DropdownMenuItem>Rename</DropdownMenuItem>
      <DropdownMenuItem>Set Duration</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
);

const RundownItem = React.forwardRef(({ item, selectedItemId, onSelectItem, onUpdateItem, ...props }, ref) => (
  <div
    ref={ref}
    {...props}
    onClick={() => onSelectItem(item.id)}
    className={`flex items-center gap-2 p-2 rounded-md transition-colors ${
      selectedItemId === item.id ? 'bg-[#FF2D86]/20' : 'hover:bg-white/5'
    }`}
  >
    <GripVertical className="w-5 h-5 text-[#A6A0AA] flex-shrink-0" />
    <div className="flex-1 min-w-0">
      <p className={`font-medium truncate ${item.skipped ? 'line-through text-[#A6A0AA]' : 'text-[#E6E1E5]'}`}>
        {item.title}
      </p>
      <div className="flex items-center gap-2 text-xs text-[#A6A0AA]">
        <span>{item.slug || 'no-slug'}</span>
        <span>•</span>
        <span>{item.durationSec}s</span>
        {item.skipped && <Badge variant="destructive" className="h-4 px-1.5 text-xs">Skipped</Badge>}
      </div>
    </div>
    <ItemContextMenu 
      isSkipped={item.skipped}
      onSkip={() => onUpdateItem(item.id, { skipped: true })}
      onUnskip={() => onUpdateItem(item.id, { skipped: false })}
    />
  </div>
));

export default function RundownTree({ episode, selectedItemId, onSelectItem, onReorderItems, onUpdateItem }) {
  const handleDragEnd = (result) => {
    if (!result.destination) return;
    const { source, destination } = result;
    if (source.droppableId !== destination.droppableId) return;

    const partId = source.droppableId;
    const part = episode.parts.find(p => p.id === partId);
    if (!part) return;

    const newItems = Array.from(part.items);
    const [reorderedItem] = newItems.splice(source.index, 1);
    newItems.splice(destination.index, 0, reorderedItem);

    onReorderItems(partId, newItems.map(item => item.id));
  };

  return (
    <div className="p-4">
      <div className="mb-4">
        <h2 className="text-xl font-bold text-[#E6E1E5]">{episode.name}</h2>
        <p className="text-sm text-[#A6A0AA]">Rundown Sequence</p>
      </div>

      <DragDropContext onDragEnd={handleDragEnd}>
        <Accordion type="multiple" defaultValue={episode.parts.map(p => p.id)} className="w-full">
          {episode.parts.map(part => (
            <AccordionItem value={part.id} key={part.id}>
              <AccordionTrigger className="font-semibold text-lg hover:no-underline">
                {part.name}
              </AccordionTrigger>
              <AccordionContent>
                <Droppable droppableId={part.id}>
                  {(provided) => (
                    <div {...provided.droppableProps} ref={provided.innerRef} className="space-y-1">
                      {part.items.map((item, index) => (
                        <Draggable key={item.id} draggableId={item.id} index={index}>
                          {(provided) => (
                            <RundownItem
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              item={item}
                              selectedItemId={selectedItemId}
                              onSelectItem={onSelectItem}
                              onUpdateItem={onUpdateItem}
                            />
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </DragDropContext>
    </div>
  );
}