import React, { useState } from 'react';
import {
  Film,
  Mic,
  Music,
  Sliders,
  Scissors,
  Lock,
} from 'lucide-react';
import type { AssemblyTimeline, AssemblyShotPlacement } from '../../api/types';
import { api } from '../../api/client';

interface AdvancedTimelinePanelProps {
  projectId: string;
  timeline: AssemblyTimeline;
  onRefresh: () => void;
}

export const AdvancedTimelinePanel: React.FC<AdvancedTimelinePanelProps> = ({
  projectId,
  timeline,
  onRefresh,
}) => {
  const [selectedPlacement, setSelectedPlacement] = useState<AssemblyShotPlacement | null>(null);
  const [trimIn, setTrimIn] = useState<number>(0.0);
  const [trimOut, setTrimOut] = useState<number>(4.0);
  const [stillDuration, setStillDuration] = useState<number>(4.0);
  const [transition, setTransition] = useState<string>('CUT');
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const handleSelectPlacement = (p: AssemblyShotPlacement) => {
    setSelectedPlacement(p);
    setTrimIn(p.trim_in);
    setTrimOut(p.trim_out || 4.0);
    setStillDuration(p.still_duration);
    setTransition(p.transition_to_next);
  };

  const handleSaveTrim = async () => {
    if (!selectedPlacement) return;
    try {
      setUpdating(true);
      setUpdateError(null);
      await api.updateShotPlacement(projectId, selectedPlacement.id, {
        trim_in: trimIn,
        trim_out: selectedPlacement.source_type === 'VIDEO' ? trimOut : undefined,
        still_duration: selectedPlacement.source_type !== 'VIDEO' ? stillDuration : undefined,
        transition_to_next: transition,
        reason: 'Updated in Advanced Timeline Panel',
      });
      onRefresh();
    } catch (err: any) {
      setUpdateError(err.message || 'Failed to update trim settings');
    } finally {
      setUpdating(false);
    }
  };

  const voClips = timeline.audio_clips.filter((c) => c.audio_type === 'VO' || c.audio_type === 'DIALOGUE');
  const bgmClips = timeline.audio_clips.filter((c) => c.audio_type === 'BGM');
  const sfxClips = timeline.audio_clips.filter((c) => c.audio_type === 'SFX' || c.audio_type === 'AMBIENCE');

  const allPlacements = timeline.scenes.flatMap((s) => s.placements);

  return (
    <div className="space-y-6">
      {/* Advanced Timeline Multi-Lane Canvas */}
      <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-5 space-y-5 shadow-xl backdrop-blur-md">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Sliders className="w-4 h-4 text-indigo-400" /> Multi-Track Timeline (Advanced Disclosure)
          </h3>
          <span className="text-xs font-mono text-slate-400">
            Total Duration: {timeline.total_duration.toFixed(1)}s
          </span>
        </div>

        {/* Lane 1: Visual Track */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-indigo-300">
            <Film className="w-3.5 h-3.5 text-indigo-400" /> Track 1: Visual Asset Placements
          </div>
          <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800 overflow-x-auto flex items-center gap-2 min-h-[80px]">
            {allPlacements.map((p) => (
              <div
                key={p.id}
                onClick={() => handleSelectPlacement(p)}
                style={{ width: `${Math.max(100, p.effective_duration * 25)}px` }}
                className={`shrink-0 h-14 rounded-lg border p-2 flex flex-col justify-between cursor-pointer transition-all hover:border-indigo-400 ${
                  selectedPlacement?.id === p.id
                    ? 'bg-indigo-950/60 border-indigo-500 ring-1 ring-indigo-500'
                    : 'bg-slate-900/90 border-slate-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-200 truncate">
                    {p.shot_title || p.shot_id.substring(0, 8)}
                  </span>
                  {p.is_locked && <Lock className="w-3 h-3 text-amber-400" />}
                </div>
                <div className="flex items-center justify-between text-[9px] text-slate-400 font-mono">
                  <span>{p.source_type}</span>
                  <span>{p.effective_duration.toFixed(1)}s</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Lane 2: VO & Dialogue Audio Track */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-emerald-300">
            <Mic className="w-3.5 h-3.5 text-emerald-400" /> Track 2: VO & Dialogue Audio
          </div>
          <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800 overflow-x-auto flex items-center gap-2 min-h-[60px]">
            {voClips.length === 0 ? (
              <span className="text-xs text-slate-500 italic">No VO or Dialogue clips assigned</span>
            ) : (
              voClips.map((clip) => (
                <div
                  key={clip.id}
                  style={{ width: `${Math.max(90, (clip.duration_seconds || 4) * 20)}px` }}
                  className="shrink-0 h-10 rounded-lg bg-emerald-950/40 border border-emerald-800/60 p-2 flex items-center justify-between"
                >
                  <span className="text-[10px] font-bold text-emerald-200 truncate">{clip.name}</span>
                  <span className="text-[9px] font-mono text-emerald-400">{clip.duration_seconds || 0}s</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Lane 3: BGM Audio Track */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-purple-300">
            <Music className="w-3.5 h-3.5 text-purple-400" /> Track 3: Background Music (BGM)
          </div>
          <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800 overflow-x-auto flex items-center gap-2 min-h-[60px]">
            {bgmClips.length === 0 ? (
              <span className="text-xs text-slate-500 italic">No BGM tracks assigned</span>
            ) : (
              bgmClips.map((clip) => (
                <div
                  key={clip.id}
                  className="w-full h-10 rounded-lg bg-purple-950/40 border border-purple-800/60 p-2 flex items-center justify-between"
                >
                  <span className="text-[10px] font-bold text-purple-200">{clip.name}</span>
                  <span className="text-[9px] font-mono text-purple-400">Loop / Mix</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Lane 4: SFX / Ambience Track */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
            <Sliders className="w-3.5 h-3.5 text-amber-400" /> Track 4: Sound Effects & Ambience (SFX)
          </div>
          <div className="bg-slate-950/80 rounded-xl p-3 border border-slate-800 overflow-x-auto flex items-center gap-2 min-h-[60px]">
            {sfxClips.length === 0 ? (
              <span className="text-xs text-slate-500 italic">No SFX or Ambience tracks assigned</span>
            ) : (
              sfxClips.map((clip) => (
                <div
                  key={clip.id}
                  className="w-full h-10 rounded-lg bg-amber-950/40 border border-amber-800/60 p-2 flex items-center justify-between"
                >
                  <span className="text-[10px] font-bold text-amber-200">{clip.name}</span>
                  <span className="text-[9px] font-mono text-amber-400">{clip.duration_seconds || 0}s</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Selected Shot Trim & Transition Drawer */}
      {selectedPlacement && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <Scissors className="w-4 h-4 text-indigo-400" /> Trim & Transition Inspector
            </h4>
            <span className="text-xs text-slate-400 font-mono">
              Placement ID: {selectedPlacement.id}
            </span>
          </div>

          {updateError && (
            <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-xl text-xs text-red-300">
              {updateError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {selectedPlacement.source_type === 'VIDEO' ? (
              <>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Trim In (sec):</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={trimIn}
                    onChange={(e) => setTrimIn(parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Trim Out (sec):</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    value={trimOut}
                    onChange={(e) => setTrimOut(parseFloat(e.target.value) || 4.0)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </>
            ) : (
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Still Image Duration (sec):</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={stillDuration}
                  onChange={(e) => setStillDuration(parseFloat(e.target.value) || 4.0)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Transition to Next:</label>
              <select
                value={transition}
                onChange={(e) => setTransition(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="CUT">CUT (Hard Cut)</option>
                <option value="FADE">FADE (Fade to Black)</option>
                <option value="DISSOLVE">DISSOLVE (Cross Dissolve)</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleSaveTrim}
                disabled={updating}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-md disabled:opacity-50"
              >
                {updating ? 'Saving...' : 'Apply Placement Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
