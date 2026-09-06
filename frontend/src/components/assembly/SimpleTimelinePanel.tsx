import React, { useState, useEffect, useCallback } from 'react';
import {
  Film,
  Play,
  Pause,
  RotateCcw,
  AlertTriangle,
  Lock,
  Unlock,
  MoveRight,
  Clock,
  Wand2,
  Bookmark,
  Volume2,
  ArrowUp,
  ArrowDown,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { api } from '../../api/client';
import type {
  AssemblyTimeline,
  AssemblyScene,
  AssemblyShotPlacement,
  TimelineCheckpoint,
} from '../../api/types';
import { AdvancedTimelinePanel } from './AdvancedTimelinePanel';

interface SimpleTimelinePanelProps {
  projectId: string;
  onRefreshProject?: () => void;
}

export const SimpleTimelinePanel: React.FC<SimpleTimelinePanelProps> = ({
  projectId,
  onRefreshProject,
}) => {
  const [timeline, setTimeline] = useState<AssemblyTimeline | null>(null);
  const [checkpoints, setCheckpoints] = useState<TimelineCheckpoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'SIMPLE' | 'ADVANCED'>('SIMPLE');

  // Preview player state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0.0);
  const [selectedPlacement, setSelectedPlacement] = useState<AssemblyShotPlacement | null>(null);

  // Checkpoint modal state
  const [checkpointLabel, setCheckpointLabel] = useState('');
  const [showCheckpointModal, setShowCheckpointModal] = useState(false);

  // Move shot modal state
  const [moveShotTarget, setMoveShotTarget] = useState<AssemblyShotPlacement | null>(null);
  const [targetSceneId, setTargetSceneId] = useState<string>('');

  const loadTimeline = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const t = await api.getAssemblyTimeline(projectId);
      setTimeline(t);

      const ckpts = await api.listTimelineCheckpoints(projectId);
      setCheckpoints(ckpts);
    } catch (err: any) {
      console.error('Failed to load assembly timeline', err);
      setError(err.message || 'Failed to load timeline assembly');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  // Preview player loop effect
  useEffect(() => {
    let interval: any = null;
    if (isPlaying && timeline && timeline.total_duration > 0) {
      interval = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= timeline.total_duration) {
            setIsPlaying(false);
            return 0.0;
          }
          return Math.min(timeline.total_duration, prev + 0.1);
        });
      }, 100);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isPlaying, timeline]);

  const handleAutoAssemble = async () => {
    try {
      setActionLoading('auto_assemble');
      setError(null);
      const updated = await api.autoAssembleTimeline(projectId);
      setTimeline(updated);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err.message || 'Auto assembly failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleApplyFix = async (blockerCode: string, fixCode: string, targetId?: string) => {
    try {
      setActionLoading('fix');
      await api.applyTimelineFix(projectId, {
        blocker_code: blockerCode,
        target_id: targetId,
        fix_code: fixCode,
      });
      await loadTimeline();
    } catch (err: any) {
      setError(err.message || 'Failed to apply recommended fix');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReorderScene = async (sceneId: string, direction: 'UP' | 'DOWN') => {
    if (!timeline) return;
    const sortedScenes = [...timeline.scenes].sort((a, b) => a.scene_order - b.scene_order);
    const index = sortedScenes.findIndex((s) => s.scene_id === sceneId);
    if (index === -1) return;
    const targetIndex = direction === 'UP' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= sortedScenes.length) return;

    // Swap orders
    const orders = sortedScenes.map((s, idx) => {
      if (idx === index) return { scene_id: s.scene_id, order: targetIndex };
      if (idx === targetIndex) return { scene_id: s.scene_id, order: index };
      return { scene_id: s.scene_id, order: idx };
    });

    try {
      setActionLoading('reorder_scene');
      const updated = await api.reorderAssemblyScenes(projectId, { orders });
      setTimeline(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to reorder scenes');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReorderShotInScene = async (scene: AssemblyScene, shotId: string, direction: 'LEFT' | 'RIGHT') => {
    const sortedPlacements = [...scene.placements].sort((a, b) => a.shot_order - b.shot_order);
    const index = sortedPlacements.findIndex((p) => p.shot_id === shotId);
    if (index === -1) return;
    const targetIndex = direction === 'LEFT' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= sortedPlacements.length) return;

    const orders = sortedPlacements.map((p, idx) => {
      if (idx === index) return { shot_id: p.shot_id, order: targetIndex };
      if (idx === targetIndex) return { shot_id: p.shot_id, order: index };
      return { shot_id: p.shot_id, order: idx };
    });

    try {
      setActionLoading('reorder_shot');
      const updated = await api.reorderShotsInScene(projectId, scene.scene_id, { orders });
      setTimeline(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to reorder shots');
    } finally {
      setActionLoading(null);
    }
  };

  const handleMoveShot = async () => {
    if (!moveShotTarget || !targetSceneId) return;
    try {
      setActionLoading('move_shot');
      const updated = await api.moveShotToScene(projectId, {
        shot_id: moveShotTarget.shot_id,
        target_scene_id: targetSceneId,
        target_position: 0,
      });
      setTimeline(updated);
      setMoveShotTarget(null);
    } catch (err: any) {
      setError(err.message || 'Failed to move shot to target scene');
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateCheckpoint = async () => {
    if (!checkpointLabel.trim()) return;
    try {
      setActionLoading('create_checkpoint');
      await api.createTimelineCheckpoint(projectId, { label: checkpointLabel.trim() });
      setCheckpointLabel('');
      setShowCheckpointModal(false);
      const ckpts = await api.listTimelineCheckpoints(projectId);
      setCheckpoints(ckpts);
    } catch (err: any) {
      setError(err.message || 'Failed to create checkpoint');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestoreCheckpoint = async (checkpointId: string) => {
    try {
      setActionLoading('restore_checkpoint');
      const restored = await api.restoreTimelineCheckpoint(projectId, checkpointId);
      setTimeline(restored);
    } catch (err: any) {
      setError(err.message || 'Failed to restore checkpoint');
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleLockPlacement = async (placement: AssemblyShotPlacement) => {
    try {
      setActionLoading('toggle_lock');
      await api.updateShotPlacement(projectId, placement.id, {
        is_locked: !placement.is_locked,
        reason: placement.is_locked ? 'User unlocked placement' : 'User locked placement',
      });
      await loadTimeline();
    } catch (err: any) {
      setError(err.message || 'Failed to toggle placement lock');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading && !timeline) {
    return (
      <div className="p-8 text-center text-slate-400 animate-pulse">
        Loading simplified timeline assembly...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Controls Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-slate-900/60 p-5 rounded-2xl border border-slate-800 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-3">
            <Film className="w-6 h-6 text-indigo-400" />
            <h2 className="text-xl font-bold text-white">Simplified Assembly & Preview</h2>
            {timeline && (
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v{timeline.version} • {timeline.status}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Backend-canonical timeline preview, auto-assembly, blocker guidance, and multi-lane disclosure.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-slate-800/80 p-1 rounded-xl border border-slate-700">
            <button
              onClick={() => setViewMode('SIMPLE')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                viewMode === 'SIMPLE'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Simple View
            </button>
            <button
              onClick={() => setViewMode('ADVANCED')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                viewMode === 'ADVANCED'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Advanced Tracks
            </button>
          </div>

          <button
            onClick={handleAutoAssemble}
            disabled={actionLoading === 'auto_assemble'}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50"
          >
            <Wand2 className="w-4 h-4" />
            {actionLoading === 'auto_assemble' ? 'Assembling...' : 'Auto Assemble'}
          </button>

          <button
            onClick={() => setShowCheckpointModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl border border-slate-700 transition-all"
          >
            <Bookmark className="w-4 h-4 text-amber-400" />
            Save Checkpoint
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 text-xs font-semibold">
            Dismiss
          </button>
        </div>
      )}

      {/* Blockers Banner with Recommended Fixes */}
      {timeline && timeline.blockers.length > 0 && (
        <div className="space-y-3">
          {timeline.blockers.map((blocker, idx) => (
            <div
              key={idx}
              className="p-4 bg-amber-950/30 border border-amber-800/50 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-amber-200">{blocker.code}</h4>
                  <p className="text-xs text-amber-300/80 mt-0.5">{blocker.message}</p>
                </div>
              </div>

              {blocker.recommended_fixes.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <span className="text-xs text-amber-400/80 font-medium">Recommended Fix:</span>
                  {blocker.recommended_fixes.map((fix, fIdx) => (
                    <button
                      key={fIdx}
                      onClick={() => handleApplyFix(blocker.code, fix.fix_code, blocker.target_id || undefined)}
                      disabled={actionLoading === 'fix'}
                      className="px-3 py-1.5 bg-amber-600/30 hover:bg-amber-600/50 border border-amber-500/40 text-amber-200 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                      {fix.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Checkpoints Restorer Header */}
      {checkpoints.length > 0 && (
        <div className="flex items-center justify-between bg-slate-900/40 p-3 px-4 rounded-xl border border-slate-800 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Bookmark className="w-4 h-4 text-amber-400" />
            <span>Checkpoints ({checkpoints.length}):</span>
          </div>
          <div className="flex items-center gap-2 overflow-x-auto">
            {checkpoints.slice(0, 5).map((ckpt) => (
              <button
                key={ckpt.id}
                onClick={() => handleRestoreCheckpoint(ckpt.id)}
                disabled={actionLoading === 'restore_checkpoint'}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md border border-slate-700 font-mono text-[11px] transition-all"
              >
                #{ckpt.checkpoint_number}: {ckpt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* View Mode Switcher Render */}
      {viewMode === 'ADVANCED' && timeline ? (
        <AdvancedTimelinePanel projectId={projectId} timeline={timeline} onRefresh={loadTimeline} />
      ) : (
        /* SIMPLE VIEW MODE */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Browser Video Preview Player */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-4 space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Play className="w-3.5 h-3.5 text-indigo-400" /> Sequence Player
                </span>
                <span className="text-xs font-mono text-indigo-300">
                  {currentTime.toFixed(1)}s / {timeline?.total_duration.toFixed(1) || '0.0'}s
                </span>
              </div>

              {/* Player Viewport Screen */}
              <div className="relative aspect-video bg-black rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center group">
                {selectedPlacement?.asset_url ? (
                  <video
                    src={selectedPlacement.asset_url}
                    className="w-full h-full object-contain"
                    controls={false}
                  />
                ) : (
                  <div className="text-center p-6 space-y-2">
                    <Film className="w-10 h-10 text-slate-600 mx-auto" />
                    <p className="text-xs text-slate-500 font-medium">
                      {selectedPlacement ? selectedPlacement.shot_title || 'Selected Shot' : 'No Shot Selected'}
                    </p>
                    {selectedPlacement && (
                      <span className="inline-block px-2 py-0.5 text-[10px] font-bold rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {selectedPlacement.source_type}
                      </span>
                    )}
                  </div>
                )}

                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-3 flex items-center justify-between">
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full transition-all shadow-md"
                  >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                  </button>

                  <button
                    onClick={() => setCurrentTime(0.0)}
                    className="p-1.5 text-slate-400 hover:text-white transition-all"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Audio Track Summary Box */}
              <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                  <span className="flex items-center gap-1.5">
                    <Volume2 className="w-4 h-4 text-emerald-400" /> Audio Summary
                  </span>
                  <span className="text-emerald-400 font-mono text-[11px]">
                    {timeline?.audio_clips.length || 0} clips
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                  <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                    <span className="block text-slate-500 text-[10px]">VO & Dialogue</span>
                    <span className="font-semibold text-slate-200">
                      {timeline?.audio_clips.filter((c) => c.audio_type === 'VO' || c.audio_type === 'DIALOGUE').length || 0} tracks
                    </span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                    <span className="block text-slate-500 text-[10px]">BGM & Ambience</span>
                    <span className="font-semibold text-slate-200">
                      {timeline?.audio_clips.filter((c) => c.audio_type === 'BGM' || c.audio_type === 'SFX' || c.audio_type === 'AMBIENCE').length || 0} tracks
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Shot Placements Sequence & Scene Cards */}
          <div className="lg:col-span-2 space-y-4">
            {!timeline || timeline.scenes.length === 0 ? (
              <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800 space-y-3">
                <Film className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-base font-bold text-slate-300">No Timeline Scenes Configured</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Click Auto Assemble above to automatically construct the initial sequence from project scenes and generated video/keyframe assets.
                </p>
                <button
                  onClick={handleAutoAssemble}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-md"
                >
                  Auto Assemble Timeline
                </button>
              </div>
            ) : (
              timeline.scenes.map((scene) => (
                <div
                  key={scene.id}
                  className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 space-y-3 backdrop-blur-sm"
                >
                  {/* Scene Header with Reorder Actions */}
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 text-xs font-mono font-bold bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30">
                        {scene.scene_title || `Scene ${scene.scene_order + 1}`}
                      </span>
                      <span className="text-xs text-slate-400">
                        ({scene.placements.length} shots)
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleReorderScene(scene.scene_id, 'UP')}
                        className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-all"
                        title="Move Scene Up"
                      >
                        <ArrowUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleReorderScene(scene.scene_id, 'DOWN')}
                        className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-all"
                        title="Move Scene Down"
                      >
                        <ArrowDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Shot Cards Horizontal Sequence */}
                  <div className="flex items-center gap-3 overflow-x-auto pb-2">
                    {scene.placements.map((placement, pIdx) => (
                      <React.Fragment key={placement.id}>
                        <div
                          onClick={() => setSelectedPlacement(placement)}
                          className={`shrink-0 w-52 bg-slate-950/70 border rounded-xl p-3 space-y-2 cursor-pointer transition-all hover:border-indigo-500/50 ${
                            selectedPlacement?.id === placement.id
                              ? 'border-indigo-500 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500'
                              : 'border-slate-800'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold text-slate-300 truncate max-w-[110px]">
                              {placement.shot_title || `Shot #${placement.shot_order + 1}`}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleToggleLockPlacement(placement);
                              }}
                              className="p-1 text-slate-400 hover:text-amber-400 rounded"
                            >
                              {placement.is_locked ? (
                                <Lock className="w-3.5 h-3.5 text-amber-400" />
                              ) : (
                                <Unlock className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>

                          {/* Asset Thumbnail Box */}
                          <div className="aspect-video bg-slate-900 rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center relative">
                            {placement.asset_thumbnail_url ? (
                              <img
                                src={placement.asset_thumbnail_url}
                                alt="Shot Asset"
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="text-center p-2">
                                <Film className="w-6 h-6 text-slate-600 mx-auto" />
                                <span className="text-[10px] font-mono text-slate-500 block mt-1">
                                  {placement.source_type}
                                </span>
                              </div>
                            )}

                            <span
                              className={`absolute top-1.5 right-1.5 px-1.5 py-0.5 text-[9px] font-bold rounded ${
                                placement.source_type === 'VIDEO'
                                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                  : placement.source_type === 'KEYFRAME'
                                  ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              }`}
                            >
                              {placement.source_type}
                            </span>
                          </div>

                          {/* Trim & Duration Info */}
                          <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                            <span className="flex items-center gap-1 font-mono text-[10px]">
                              <Clock className="w-3 h-3 text-slate-500" /> {placement.effective_duration.toFixed(1)}s
                            </span>
                            <span className="text-[10px] font-semibold text-indigo-400">
                              {placement.transition_to_next}
                            </span>
                          </div>

                          {/* Card Reorder & Move Action Buttons */}
                          <div className="flex items-center justify-between pt-1 border-t border-slate-900 text-[10px]">
                            <div className="flex items-center gap-1">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleReorderShotInScene(scene, placement.shot_id, 'LEFT');
                                }}
                                className="p-1 hover:bg-slate-800 text-slate-400 hover:text-white rounded"
                                title="Move Left"
                              >
                                ←
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleReorderShotInScene(scene, placement.shot_id, 'RIGHT');
                                }}
                                className="p-1 hover:bg-slate-800 text-slate-400 hover:text-white rounded"
                                title="Move Right"
                              >
                                →
                              </button>
                            </div>

                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setMoveShotTarget(placement);
                              }}
                              className="text-indigo-400 hover:text-indigo-300 font-semibold"
                            >
                              Move Scene...
                            </button>
                          </div>
                        </div>

                        {pIdx < scene.placements.length - 1 && (
                          <ChevronRight className="w-4 h-4 text-slate-600 shrink-0" />
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Save Checkpoint Modal */}
      {showCheckpointModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Bookmark className="w-5 h-5 text-amber-400" /> Save Timeline Checkpoint
            </h3>
            <p className="text-xs text-slate-400">
              Create an immutable snapshot of current timeline placements, transitions, and trim state.
            </p>
            <input
              type="text"
              placeholder="e.g. Cut 1 Approved by Director"
              value={checkpointLabel}
              onChange={(e) => setCheckpointLabel(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
            />
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowCheckpointModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCheckpoint}
                disabled={!checkpointLabel.trim() || actionLoading === 'create_checkpoint'}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-xl disabled:opacity-50"
              >
                Save Snapshot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Move Shot Modal */}
      {moveShotTarget && timeline && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <MoveRight className="w-5 h-5 text-indigo-400" /> Move Shot to Scene
            </h3>
            <p className="text-xs text-slate-400">
              Cross-scene shot movements require explicit scene assignment.
            </p>
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 block">Target Scene:</label>
              <select
                value={targetSceneId}
                onChange={(e) => setTargetSceneId(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">Select target scene...</option>
                {timeline.scenes.map((s) => (
                  <option key={s.scene_id} value={s.scene_id}>
                    {s.scene_title || `Scene ${s.scene_order + 1}`}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setMoveShotTarget(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleMoveShot}
                disabled={!targetSceneId || actionLoading === 'move_shot'}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl disabled:opacity-50"
              >
                Move Shot
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
