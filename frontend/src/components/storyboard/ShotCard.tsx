import React from 'react';
import type { Shot, GenerationJob } from '../../api/types';
import { Lock, Unlock, Play, Clock, AlertCircle, CheckCircle2, Film } from 'lucide-react';

interface ShotCardProps {
  shot: Shot;
  latestJob?: GenerationJob;
  isSelected: boolean;
  onSelect: () => void;
  onToggleLock: (e: React.MouseEvent) => void;
}

export const ShotCard: React.FC<ShotCardProps> = ({
  shot,
  latestJob,
  isSelected,
  onSelect,
  onToggleLock,
}) => {
  const getJobStatusBadge = () => {
    if (!latestJob) {
      return (
        <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
          Not Generated
        </span>
      );
    }

    switch (latestJob.status) {
      case 'COMPLETED':
        return (
          <span
            style={{
              color: '#34d399',
              fontSize: '0.7rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <CheckCircle2 size={11} /> Ready
          </span>
        );
      case 'FAILED':
        return (
          <span
            style={{
              color: 'var(--accent-rose)',
              fontSize: '0.7rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <AlertCircle size={11} /> Failed
          </span>
        );
      case 'RECONCILIATION_REQUIRED':
        return (
          <span
            style={{
              color: 'var(--accent-amber)',
              fontSize: '0.7rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <AlertCircle size={11} /> Reconcile
          </span>
        );
      default:
        return (
          <span
            style={{
              color: '#818cf8',
              fontSize: '0.7rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Play size={11} /> {latestJob.status}
          </span>
        );
    }
  };

  return (
    <div
      onClick={onSelect}
      style={{
        backgroundColor: 'var(--bg-card)',
        border: isSelected
          ? '2px solid var(--primary)'
          : '1px solid var(--border-subtle)',
        borderRadius: '8px',
        overflow: 'hidden',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.15s ease',
        boxShadow: isSelected ? '0 0 0 1px var(--primary)' : 'none',
      }}
      data-testid={`shot-card-${shot.id}`}
    >
      {/* Thumbnail Area */}
      <div
        style={{
          height: '110px',
          backgroundColor: '#0a0e17',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        {latestJob?.result_video_url ? (
          <video
            src={latestJob.result_video_url}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            muted
            loop
            onMouseOver={(e) => (e.target as HTMLVideoElement).play()}
            onMouseOut={(e) => (e.target as HTMLVideoElement).pause()}
          />
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            <Film size={24} style={{ marginBottom: '4px' }} />
            <div style={{ fontSize: '0.65rem' }}>Visual Placeholder</div>
          </div>
        )}

        {/* Lock Overlay Badge */}
        <button
          onClick={onToggleLock}
          style={{
            position: 'absolute',
            top: '6px',
            right: '6px',
            backgroundColor: shot.is_locked ? 'rgba(239, 68, 68, 0.8)' : 'rgba(0, 0, 0, 0.5)',
            color: '#fff',
            borderRadius: '4px',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title={shot.is_locked ? 'Shot is LOCKED (Click to unlock)' : 'Shot is UNLOCKED (Click to lock)'}
          data-testid={`shot-lock-toggle-${shot.id}`}
        >
          {shot.is_locked ? <Lock size={12} /> : <Unlock size={12} />}
        </button>

        {/* Duration badge */}
        <div
          style={{
            position: 'absolute',
            bottom: '6px',
            left: '6px',
            backgroundColor: 'rgba(0,0,0,0.7)',
            color: '#cbd5e1',
            borderRadius: '3px',
            padding: '2px 5px',
            fontSize: '0.65rem',
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
          }}
        >
          <Clock size={10} /> {shot.duration_seconds}s
        </div>
      </div>

      {/* Details Body */}
      <div style={{ padding: '10px 12px', flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontWeight: '600', fontSize: '0.8125rem' }}>
            Shot #{shot.shot_number}
          </span>
          <span
            style={{
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              background: 'var(--bg-input)',
              padding: '2px 5px',
              borderRadius: '3px',
            }}
          >
            {shot.shot_type.replace('_', ' ')}
          </span>
        </div>

        {/* Prompt snippet */}
        <p
          style={{
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            lineHeight: '1.3',
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            minHeight: '2rem',
          }}
        >
          {shot.visual_prompt || shot.video_prompt || shot.action || '(No prompt set)'}
        </p>

        {/* Status footer */}
        <div
          style={{
            marginTop: 'auto',
            paddingTop: '6px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          {getJobStatusBadge()}
          {shot.is_locked && (
            <span style={{ fontSize: '0.65rem', color: 'var(--accent-rose)' }}>
              Locked
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
