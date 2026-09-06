import React, { useState, useEffect, useCallback } from 'react';
import {
  Volume2,
  Mic,
  Music,
  Sparkles,
  Wind,
  Sliders,
  Play,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Lock,
  Unlock,
  VolumeX,
} from 'lucide-react';
import { api } from '../../api/client';
import type { AudioClip, AudioPlan } from '../../api/types';

interface AudioProductionPanelProps {
  projectId: string;
  projectStatus?: string;
  onRefreshProject?: () => void;
}

export const AudioProductionPanel: React.FC<AudioProductionPanelProps> = ({
  projectId,
  projectStatus,
  onRefreshProject,
}) => {
  const [plan, setPlan] = useState<AudioPlan | null>(null);
  const [clips, setClips] = useState<AudioClip[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mixMetadata, setMixMetadata] = useState<any | null>(null);

  const loadAudioData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      try {
        const p = await api.getAudioPlan(projectId);
        setPlan(p);
        if (p?.plan_data?.auto_mix) {
          setMixMetadata(p.plan_data.auto_mix);
        }
      } catch (err: any) {
        // Plan might not exist yet
        setPlan(null);
      }

      const cList = await api.listAudioClips(projectId);
      const items = Array.isArray(cList) ? cList : (cList?.items || []);
      setClips(items);
    } catch (err: any) {
      console.error('Failed to load audio data', err);
      setError(err.message || 'Failed to load audio data');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadAudioData();
  }, [loadAudioData]);

  const handleGeneratePlan = async () => {
    try {
      setActionLoading('plan');
      setError(null);
      const newPlan = await api.generateAudioPlan(projectId);
      setPlan(newPlan);
      await loadAudioData();
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err.message || 'Failed to generate audio plan');
    } finally {
      setActionLoading(null);
    }
  };

  const handleApprovePlan = async () => {
    try {
      setActionLoading('approve_plan');
      setError(null);
      const approved = await api.approveAudioPlan(projectId);
      setPlan(approved);
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err.message || 'Failed to approve audio plan');
    } finally {
      setActionLoading(null);
    }
  };

  const handleBatchAction = async (action: string) => {
    try {
      setActionLoading(action);
      setError(null);
      await api.executeAudioBatch(projectId, { action, cost_authorized: true });
      await loadAudioData();
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err.message || `Failed to execute ${action}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleGenerateClip = async (clipId: string) => {
    try {
      setActionLoading(`clip_${clipId}`);
      setError(null);
      await api.generateClipAudio(projectId, clipId, { cost_authorized: true });
      await loadAudioData();
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err.message || 'Failed to generate audio clip');
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleLock = async (clip: AudioClip) => {
    try {
      let updated: AudioClip;
      if (clip.is_locked) {
        updated = await api.unlockAudioClip(projectId, clip.id, { reason: 'Explicit user unlock' });
      } else {
        updated = await api.lockAudioClip(projectId, clip.id, { reason: 'User locked clip' });
      }
      setClips((prev) =>
        prev.map((c) => (c.id === clip.id ? updated : c))
      );
    } catch (err: any) {
      setError(err.message || 'Failed to toggle lock');
    }
  };

  const handleUpdateClip = async (clipId: string, updates: Partial<AudioClip>) => {
    try {
      await api.updateAudioClip(projectId, clipId, updates);
      setClips((prev) =>
        prev.map((c) => (c.id === clipId ? { ...c, ...updates } : c))
      );
    } catch (err: any) {
      setError(err.message || 'Failed to update clip');
    }
  };

  const handleComputeAutoMix = async () => {
    try {
      setActionLoading('auto_mix');
      setError(null);
      const mix = await api.computeAudioMix(projectId);
      setMixMetadata(mix);
      await loadAudioData();
      if (onRefreshProject) onRefreshProject();
    } catch (err: any) {
      setError(err.message || 'Failed to compute auto-mix');
    } finally {
      setActionLoading(null);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'VO':
      case 'DIALOGUE':
        return <Mic size={16} color="#818cf8" />;
      case 'BGM':
        return <Music size={16} color="#fbbf24" />;
      case 'SFX':
        return <Sparkles size={16} color="#34d399" />;
      case 'AMBIENCE':
        return <Wind size={16} color="#22d3ee" />;
      default:
        return <Volume2 size={16} color="#94a3b8" />;
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        padding: '20px',
      }}
      data-testid="audio-production-panel"
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Volume2 size={24} color="#818cf8" />
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>
              Audio Production & Mixing
            </h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
              {projectStatus ? `Stage: ${projectStatus} • ` : ''}Core V1 provider-neutral audio tracks, voiceover, score, and speech-over-music auto-ducking.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            onClick={handleGeneratePlan}
            disabled={actionLoading !== null}
            data-testid="generate-audio-plan-btn"
          >
            <RefreshCw size={14} className={actionLoading === 'plan' ? 'spin' : ''} />
            {plan ? 'Refresh Plan' : 'Generate Audio Plan'}
          </button>

          {plan && plan.status !== 'APPROVED' && (
            <button
              className="btn btn-primary"
              onClick={handleApprovePlan}
              disabled={actionLoading !== null}
              data-testid="approve-audio-plan-btn"
            >
              <CheckCircle size={14} />
              Approve Audio Plan
            </button>
          )}

          <button
            className="btn btn-secondary"
            onClick={() => handleBatchAction('GENERATE_ALL_VO')}
            disabled={actionLoading !== null || clips.length === 0}
            data-testid="generate-all-vo-btn"
          >
            <Mic size={14} />
            Batch VO
          </button>

          <button
            className="btn btn-secondary"
            onClick={() => handleBatchAction('ASSIGN_BGM')}
            disabled={actionLoading !== null || clips.length === 0}
            data-testid="assign-bgm-btn"
          >
            <Music size={14} />
            Assign BGM
          </button>

          <button
            className="btn btn-secondary"
            onClick={handleComputeAutoMix}
            disabled={actionLoading !== null || clips.length === 0}
            data-testid="compute-auto-mix-btn"
          >
            <Sliders size={14} />
            Auto-Mix & Ducking
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '6px',
            padding: '10px 14px',
            marginBottom: '16px',
            color: '#f87171',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Plan Summary Banner */}
      {plan && (
        <div
          style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-default)',
            borderRadius: '8px',
            padding: '12px 16px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.8125rem',
            flexWrap: 'wrap',
            gap: '10px',
          }}
        >
          <div>
            <strong>Audio Plan Status:</strong>{' '}
            <span
              className={`badge badge-${plan.status === 'APPROVED' ? 'approved' : 'draft'}`}
              style={{ marginLeft: '4px' }}
            >
              {plan.status}
            </span>
            <span style={{ marginLeft: '12px', color: 'var(--text-secondary)' }}>
              Version {plan.version} | Total Tracks: {clips.length}
            </span>
          </div>

          {mixMetadata && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-approved">
                Auto-Ducking: {mixMetadata.default_ducking_amount_db || -12} dB
              </span>
              <span style={{ color: 'var(--text-secondary)' }}>
                Speech Segments: {mixMetadata.speech_intervals?.length || 0}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Track List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
          Loading audio tracks...
        </div>
      ) : clips.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '40px',
            backgroundColor: 'var(--bg-card)',
            borderRadius: '8px',
            border: '1px dashed var(--border-subtle)',
          }}
        >
          <p style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>
            No audio tracks created yet. Generate an audio plan to initialize VO, BGM, SFX, and Ambience tracks.
          </p>
          <button className="btn btn-primary" onClick={handleGeneratePlan} disabled={actionLoading !== null}>
            <RefreshCw size={14} />
            Generate Audio Plan
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {clips.map((clip) => {
            const isGenerating = actionLoading === `clip_${clip.id}` || clip.status === 'SUBMITTING';
            return (
              <div
                key={clip.id}
                className="card"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-default)',
                  gap: '12px',
                  flexWrap: 'wrap',
                }}
                data-testid={`audio-clip-${clip.id}`}
              >
                {/* Info & Badges */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: '240px' }}>
                  {getTypeIcon(clip.audio_type)}
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{clip.name}</div>
                    <div
                      style={{
                        display: 'flex',
                        gap: '6px',
                        marginTop: '4px',
                        fontSize: '0.7rem',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      <span className="badge badge-draft">{clip.audio_type}</span>
                      <span className="badge badge-draft">{clip.source_type}</span>
                      <span className="badge badge-draft">{clip.generation_mode}</span>
                      <span className="badge badge-draft">{clip.scope}</span>
                    </div>
                  </div>
                </div>

                {/* Prompt preview */}
                <div
                  style={{
                    flex: 1,
                    minWidth: '200px',
                    fontSize: '0.8125rem',
                    color: 'var(--text-secondary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={clip.prompt || ''}
                >
                  {clip.speaker && <strong>[{clip.speaker}] </strong>}
                  {clip.prompt || 'No prompt specified'}
                </div>

                {/* Controls: Volume, Mute, Ducking */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
                    <span>Vol:</span>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={clip.volume}
                      onChange={(e) =>
                        handleUpdateClip(clip.id, { volume: parseFloat(e.target.value) })
                      }
                      style={{ width: '60px' }}
                    />
                    <span>{Math.round(clip.volume * 100)}%</span>
                  </div>

                  <button
                    className={`btn btn-sm ${clip.mute ? 'btn-danger' : 'btn-secondary'}`}
                    onClick={() => handleUpdateClip(clip.id, { mute: !clip.mute })}
                    title={clip.mute ? 'Unmute' : 'Mute'}
                  >
                    {clip.mute ? <VolumeX size={14} /> : <Volume2 size={14} />}
                  </button>

                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => handleToggleLock(clip)}
                    title={clip.is_locked ? 'Unlock' : 'Lock'}
                    data-testid={`toggle-lock-${clip.id}`}
                  >
                    {clip.is_locked ? <Lock size={14} color="#f59e0b" /> : <Unlock size={14} />}
                  </button>

                  {/* Status */}
                  <span
                    className={`badge badge-${
                      clip.status === 'READY'
                        ? 'approved'
                        : clip.status === 'FAILED' || clip.status === 'RECONCILIATION_REQUIRED'
                        ? 'danger'
                        : 'draft'
                    }`}
                  >
                    {clip.status}
                  </span>

                  {/* Generate Button */}
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => handleGenerateClip(clip.id)}
                    disabled={isGenerating || clip.is_locked}
                    data-testid={`generate-clip-${clip.id}`}
                  >
                    <Play size={12} className={isGenerating ? 'spin' : ''} />
                    {clip.status === 'READY' ? 'Regenerate' : 'Generate'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
