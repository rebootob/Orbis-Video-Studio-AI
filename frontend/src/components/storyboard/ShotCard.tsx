import React from 'react';
import type { Shot, GenerationJob } from '../../api/types';
import { Lock, Unlock, Play, Clock, AlertCircle, CheckCircle2, Film, ChevronUp, ChevronDown } from 'lucide-react';

interface ShotCardProps {
  shot: Shot;
  latestJob?: GenerationJob;
  isSelected: boolean;
  isMultiSelected?: boolean;
  canMoveUp?: boolean;
  canMoveDown?: boolean;
  onSelect: () => void;
  onToggleSelect?: (e: React.MouseEvent) => void;
  onToggleLock: (e: React.MouseEvent) => void;
  onMoveUp?: (e: React.MouseEvent) => void;
  onMoveDown?: (e: React.MouseEvent) => void;
}

export const ShotCard: React.FC<ShotCardProps> = ({
  shot,
  latestJob,
  isSelected,
  isMultiSelected = false,
  canMoveUp = false,
  canMoveDown = false,
  onSelect,
  onToggleSelect,
  onToggleLock,
  onMoveUp,
  onMoveDown,
}) => {
  const getJobStatusBadge = () => {
    if (!latestJob) {
      if (shot.keyframe_url) {
        return (
          <span style={{ color: '#38bdf8', fontSize: '0.7rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle2 size={11} /> Keyframe
          </span>
        );
      }
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
          : isMultiSelected
          ? '1px solid var(--primary)'
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
        ) : shot.keyframe_url ? (
          <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            <img
              src={shot.keyframe_url}
              alt={`Shot ${shot.shot_number} Keyframe`}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              loading="lazy"
            />
            <div
              style={{
                position: 'absolute',
                bottom: '4px',
                right: '4px',
                backgroundColor: 'rgba(0,0,0,0.7)',
                color: '#38bdf8',
                fontSize: '0.6rem',
                padding: '1px 5px',
                borderRadius: '3px',
                fontWeight: 600,
                letterSpacing: '0.5px',
              }}
            >
              KEYFRAME
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            <Film size={24} style={{ marginBottom: '4px' }} />
            <div style={{ fontSize: '0.65rem' }}>Visual Blueprint</div>
          </div>
        )}

        {/* Multi-Select Checkbox */}
        {onToggleSelect && (
          <div
            onClick={onToggleSelect}
            style={{
              position: 'absolute',
              top: '6px',
              left: '6px',
              backgroundColor: isMultiSelected ? 'var(--primary)' : 'rgba(0,0,0,0.6)',
              borderRadius: '4px',
              padding: '2px 4px',
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              border: '1px solid rgba(255,255,255,0.3)',
            }}
            title="Select for batch action"
          >
            <input
              type="checkbox"
              checked={isMultiSelected}
              onChange={() => {}}
              style={{ cursor: 'pointer', margin: 0 }}
            />
          </div>
        )}

        {/* Reorder Up / Down Controls */}
        <div
          style={{
            position: 'absolute',
            top: '6px',
            right: '34px',
            display: 'flex',
            gap: '2px',
          }}
        >
          {canMoveUp && onMoveUp && (
            <button
              onClick={onMoveUp}
              style={{
                backgroundColor: 'rgba(0,0,0,0.6)',
                color: '#fff',
                border: 'none',
                borderRadius: '3px',
                padding: '2px',
                cursor: 'pointer',
                display: 'flex',
              }}
              title="Move shot up"
            >
              <ChevronUp size={12} />
            </button>
          )}
          {canMoveDown && onMoveDown && (
            <button
              onClick={onMoveDown}
              style={{
                backgroundColor: 'rgba(0,0,0,0.6)',
                color: '#fff',
                border: 'none',
                borderRadius: '3px',
                padding: '2px',
                cursor: 'pointer',
                display: 'flex',
              }}
              title="Move shot down"
            >
              <ChevronDown size={12} />
            </button>
          )}
        </div>

        {/* Lock Overlay Badge */}
        <button
          onClick={onToggleLock}
          style={{
            position: 'absolute',
            top: '6px',
            right: '6px',
            backgroundColor: shot.is_locked ? 'rgba(239, 68, 68, 0.8)' : 'rgba(0, 0, 0, 0.6)',
            color: '#fff',
            borderRadius: '4px',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: 'none',
            cursor: 'pointer',
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
