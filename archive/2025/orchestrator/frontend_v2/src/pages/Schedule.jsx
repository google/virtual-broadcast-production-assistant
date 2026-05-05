import { useEffect, useReducer, useCallback } from 'react';
import { Toaster, toast } from 'sonner';
import ScheduleActionBar from '../components/schedule/ScheduleActionBar';
import RundownTree from '../components/schedule/RundownTree';
import ScheduleTimeline from '../components/schedule/ScheduleTimeline';

// --- Data (previously in data/mockSchedule.js) ---
const mockEpisodeData = {
  id: "ep-001",
  name: "Evening News — 18:00",
  parts: [
    {
      id: "p-1",
      name: "Headlines",
      items: [
        { id: "i-101", title: "Starts on black", category: "VIDEO", durationSec: 10, skipped: false },
        { id: "i-102", title: "Tight out", category: "VIDEO", durationSec: 10, skipped: false },
      ],
    },
    {
      id: "p-2",
      name: "Main",
      items: [
        { id: "i-201", title: "Missing clip", slug: "SLUG/CLIPNAME/1826", category: "VIDEO", durationSec: 120, skipped: false },
        { id: "i-202", title: "Distorted audio on clip", slug: "SLUG/CLIPNAME/1826", category: "AUDIO", durationSec: 90, skipped: false },
        { id: "i-203", title: "Illegal frames on clip", slug: "SLUG/CLIPNAME/1826", category: "VIDEO", durationSec: 30, skipped: true },
        { id: "i-204", title: "Video aspect ratio mismatch", category: "CHECKS", durationSec: 20, skipped: false },
        { id: "i-205", title: "Missing graphic", slug: "Item 01 — Story strap", category: "GFX", durationSec: 15, skipped: false },
      ],
    },
    {
      id: "p-3",
      name: "Weather & Sport",
      items: [
        { id: "i-301", title: "Weather Forecast", category: "GFX", durationSec: 180, skipped: false },
        { id: "i-302", title: "Sports Highlights", category: "VIDEO", durationSec: 240, skipped: false },
      ],
    },
  ],
};

// --- Store Logic (previously in hooks/useScheduleStore.js) ---
const deepClone = (obj) => JSON.parse(JSON.stringify(obj));

const initialState = {
  episode: null,
  originalEpisode: null,
  history: [],
  future: [],
  pending: false,
  error: null,
  selectedItemId: null,
};

const reducer = (state, action) => {
  switch (action.type) {
    case 'LOAD_START':
      return { ...state, pending: true, error: null };
    case 'LOAD_SUCCESS': {
      const episode = deepClone(action.payload);
      return {
        ...initialState,
        episode,
        originalEpisode: deepClone(episode),
        pending: false,
      };
    }
    case 'LOAD_FAILURE':
      return { ...state, pending: false, error: action.payload };
    case 'SET_STATE': {
      const { episode } = state;
      const newEpisode = action.payload(deepClone(episode));
      return {
        ...state,
        episode: newEpisode,
        history: [...state.history, deepClone(state.episode)],
        future: [],
      };
    }
    case 'APPLY_START':
      return { ...state, pending: true, error: null };
    case 'APPLY_SUCCESS': {
        const newEpisode = deepClone(action.payload);
        return {
            ...initialState,
            episode: newEpisode,
            originalEpisode: deepClone(newEpisode),
            pending: false,
        };
    }
    case 'APPLY_FAILURE':
        return { ...state, pending: false, error: action.payload };
    case 'DISCARD':
      return {
        ...initialState,
        episode: deepClone(state.originalEpisode),
        originalEpisode: deepClone(state.originalEpisode),
      };
    case 'UNDO': {
      if (state.history.length === 0) return state;
      const previous = state.history[state.history.length - 1];
      const newHistory = state.history.slice(0, state.history.length - 1);
      return {
        ...state,
        episode: deepClone(previous),
        history: newHistory,
        future: [deepClone(state.episode), ...state.future],
      };
    }
    case 'REDO': {
      if (state.future.length === 0) return state;
      const next = state.future[0];
      const newFuture = state.future.slice(1);
      return {
        ...state,
        episode: deepClone(next),
        history: [...state.history, deepClone(state.episode)],
        future: newFuture,
      };
    }
    case 'SELECT_ITEM':
        return { ...state, selectedItemId: action.payload };
    default:
      return state;
  }
};

const useScheduleStore = () => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const loadEpisode = useCallback(async () => {
    dispatch({ type: 'LOAD_START' });
    try {
      await new Promise(resolve => setTimeout(resolve, 500)); 
      const data = mockEpisodeData;
      
      dispatch({ type: 'LOAD_SUCCESS', payload: data });
      toast.info("Showing placeholder rundown.", {
          description: "Server endpoints not available.",
      });
    } catch (error) {
      dispatch({ type: 'LOAD_FAILURE', payload: error.message });
      dispatch({ type: 'LOAD_SUCCESS', payload: mockEpisodeData });
      throw error;
    }
  }, []);

  const setStateWithHistory = useCallback((updateFn) => {
    dispatch({ type: 'SET_STATE', payload: updateFn });
  }, []);

  const reorderItems = useCallback((partId, itemOrder) => {
    setStateWithHistory(episode => {
      const part = episode.parts.find(p => p.id === partId);
      if (part) {
        const itemMap = new Map(part.items.map(item => [item.id, item]));
        part.items = itemOrder.map(id => itemMap.get(id));
      }
      return episode;
    });
  }, [setStateWithHistory]);

  const updateItem = useCallback((itemId, patch) => {
    setStateWithHistory(episode => {
        for (const part of episode.parts) {
            const item = part.items.find(i => i.id === itemId);
            if (item) {
                Object.assign(item, patch);
                break;
            }
        }
        return episode;
    });
  }, [setStateWithHistory]);

  const selectItem = useCallback((itemId) => {
      dispatch({ type: 'SELECT_ITEM', payload: itemId });
  }, []);

  const undo = useCallback(() => dispatch({ type: 'UNDO' }), []);
  const redo = useCallback(() => dispatch({ type: 'REDO' }), []);
  const discardChanges = useCallback(() => dispatch({ type: 'DISCARD' }), []);

  const applyChanges = useCallback(async () => {
    dispatch({ type: 'APPLY_START' });
    try {
        await new Promise(resolve => setTimeout(resolve, 1000));
        toast.success("Local preview only (server endpoints not available).", {
            description: "Changes have been applied locally."
        });
        dispatch({ type: 'APPLY_SUCCESS', payload: state.episode });
    } catch (err) {
        toast.error("Failed to apply changes.", {
            description: err.message,
        });
        dispatch({ type: 'APPLY_FAILURE', payload: err.message });
        dispatch({ type: 'DISCARD' });
    }
  }, [state.episode]);

  return {
    state,
    loadEpisode,
    reorderItems,
    updateItem,
    applyChanges,
    discardChanges,
    undo,
    redo,
    selectItem,
  };
};

// --- Page Component ---
export default function SchedulePage() {
  const {
    state,
    loadEpisode,
    reorderItems,
    updateItem,
    applyChanges,
    discardChanges,
    undo,
    redo,
    selectItem,
  } = useScheduleStore();

  useEffect(() => {
    loadEpisode().catch(error => {
      toast.error("Couldn't load rundown; showing placeholders.", {
        description: error.message,
      });
    });
  }, [loadEpisode]);

  const { episode, originalEpisode, history, future, selectedItemId, pending, error } = state;

  if (!episode) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)]">
        <div className="flex items-center gap-3 text-[#A6A0AA]">
          <div className="w-6 h-6 border-2 border-current border-t-transparent rounded-full animate-spin" />
          <span>Loading Rundown...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] bg-[#0D0B12]">
      <Toaster richColors theme="dark" />
      <ScheduleActionBar
        onApply={applyChanges}
        onDiscard={discardChanges}
        onUndo={undo}
        onRedo={redo}
        hasChanges={JSON.stringify(episode) !== JSON.stringify(originalEpisode)}
        canUndo={history.length > 0}
        canRedo={future.length > 0}
        isPending={pending}
        error={error}
      />
      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/3 min-w-[350px] max-w-[500px] bg-[#1C1A22] border-r border-white/8 overflow-y-auto">
          <RundownTree
            episode={episode}
            selectedItemId={selectedItemId}
            onSelectItem={selectItem}
            onReorderItems={reorderItems}
            onUpdateItem={updateItem}
          />
        </div>
        <div className="flex-1 overflow-y-auto">
          <ScheduleTimeline 
            episode={episode} 
            selectedItemId={selectedItemId}
            onSelectItem={selectItem}
          />
        </div>
      </div>
    </div>
  );
}