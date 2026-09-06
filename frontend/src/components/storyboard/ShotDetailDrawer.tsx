import React, { useState, useEffect, useRef } from 'react';
import type { Shot, ShotType, GenerationJob } from '../../api/types';
import {
  X,
  Lock,
  Unlock,
  Play,
  Archive,
  Save,
  CheckCircle2,
  Clock,
  Film,
  Sparkles,
  ChevronDown,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';

interface ShotDetailDrawerProps {
  shot: Shot | null;
  latestJob?: GenerationJob;
  projectStatus?: string;
  onClose: () => void;
  onUpdateShot: (shotId: string, payload: Partial<Shot>) => Promise<void>;
  onDeleteShot: (shotId: string) => Promise<void>;
  onToggleLock: (shot: Shot) => Promise<void>;
  onGenerateShot: (shotId: string) => Promise<void>;
}

export const ShotDetailDrawer: React.FC<ShotDetailDrawerProps> = ({
  shot,
  latestJob,
  projectStatus,
  onClose,
  onUpdateShot,
  onDeleteShot,
  onToggleLock,
  onGenerateShot,
}) => {
  const [visualPrompt, setVisualPrompt] = useState('');
  const [shotType, setShotType] = useState<ShotType>('AI_GENERATED');
  const [durationSeconds, setDurationSeconds] = useState(4);
  const [camera, setCamera] = useState('');
  const [subject, setSubject] = useState('');
  const [action, setAction] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'SAVED' | 'SAVING' | 'DIRTY' | null>(null);

  const isInitialMount = useRef(true);

  useEffect(() => {
    if (shot) {
      isInitialMount.current = true;
      setVisualPrompt(shot.visual_prompt || shot.video_prompt || '');
      setShotType(shot.shot_type);
      setDurationSeconds(shot.duration_seconds || 4);
      setCamera(shot.camera || '');
      setSubject(shot.subject || '');
      setAction(shot.action || '');
      setSaveStatus(null);
    }
  }, [shot]);

  // Mark dirty when user types
  const markDirty = () => {
    if (!shot?.is_locked) {
      setSaveStatus('DIRTY');
    }
  };

  const handleSafeClose = () => {
    if (saveStatus === 'DIRTY') {
      if (!confirm('You have unsaved changes in this shot. Discard changes and close?')) {
        return;
      }
    }
    onClose();
  };

  if (!shot) return null;

  const handleSave = async () => {
    if (shot.is_locked) return;
    try {
      setSaving(true);
      setSaveStatus('SAVING');
      await onUpdateShot(shot.id, {
        visual_prompt: visualPrompt,
        video_prompt: visualPrompt,
        shot_type: shotType,
        duration_seconds: durationSeconds,
        camera: camera || undefined,
        subject: subject || undefined,
        action: action || undefined,
      });
      setSaveStatus('SAVED');
      setTimeout(() => setSaveStatus(null), 2500);
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
      setSaveStatus('DIRTY');
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      await onGenerateShot(shot.id);
    } catch (err: any) {
      alert(`Generation trigger failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '440px',
        maxWidth: '100vw',
        backgroundColor: 'var(--bg-panel)',
        borderLeft: '1px solid var(--border-default)',
        boxShadow: '-10px 0 25px rgba(0,0,0,0.5)',
        zIndex: 90,
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
      }}
      data-testid="shot-detail-drawer"
    >
      {/* Drawer Header */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Film size={18} color="#818cf8" />
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
            Shot #{shot.shot_number} Details
          </h3>
          {shot.is_locked && (
            <span className="badge badge-locked" style={{ fontSize: '0.65rem' }}>
              Locked
            </span>
          )}
        </div>
        <button className="btn btn-xs btn-outline" onClick={handleSafeClose} data-testid="shot-drawer-close-btn" title="Close drawer">
          <X size={16} />
        </button>
      </div>

      {/* Drawer Body */}
      <div style={{ padding: '20px', flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Preview Container */}
        <div
          style={{
            height: '180px',
            backgroundColor: '#0a0e17',
            borderRadius: '8px',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {latestJob?.result_video_url ? (
            <video
              src={latestJob.result_video_url}
              controls
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          ) : (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              <Sparkles size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
              <p style={{ fontSize: '0.8125rem' }}>No generated video yet</p>
              <span style={{ fontSize: '0.7rem' }}>
                Status: {latestJob?.status || 'NOT_DISPATCHED'}
              </span>
            </div>
          )}
        </div>

        {/* Lock / Generate Action Toolbar */}
        {(() => {
          const allowedProductionStatuses = [
            'SHOT_PLAN_APPROVED',
            'IMAGES_GENERATED',
            'VIDEO_IN_PROGRESS',
          ];
          const isProductionGated = Boolean(projectStatus && !allowedProductionStatuses.includes(projectStatus));

          return (
            <>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className={`btn btn-sm ${shot.is_locked ? 'btn-danger' : 'btn-outline'}`}
                  style={{ flex: 1 }}
                  onClick={() => onToggleLock(shot)}
                  data-testid="drawer-lock-toggle-btn"
                >
                  {shot.is_locked ? <Unlock size={14} /> : <Lock size={14} />}
                  {shot.is_locked ? 'Unlock Shot' : 'Lock Shot'}
                </button>

                <button
                  className="btn btn-sm btn-primary"
                  style={{ flex: 1 }}
                  onClick={handleGenerate}
                  disabled={shot.is_locked || generating || isProductionGated}
                  data-testid="drawer-generate-shot-btn"
                  title={
                    isProductionGated
                      ? 'Shot Plan must be approved before production generation.'
                      : shot.is_locked
                      ? 'Shot is locked'
                      : 'Generate video for this shot'
                  }
                >
                  <Play size={14} />
                  {generating ? 'Dispatching...' : 'Generate Shot'}
                </button>
              </div>

              {isProductionGated && (
                <div className="alert alert-warning" style={{ fontSize: '0.75rem', padding: '8px 12px' }} data-testid="drawer-production-gated-warning">
                  <AlertCircle size={14} />
                  Shot Plan must be approved before production generation.
                </div>
              )}
            </>
          );
        })()}

        {shot.is_locked && (
          <div className="alert alert-warning" style={{ fontSize: '0.75rem', padding: '8px 12px' }}>
            <AlertCircle size={14} />
            This shot is locked. Modifications and regeneration are prevented until unlocked.
          </div>
        )}

        {/* Visual / Video Prompt */}
        <div className="form-group">
          <label className="form-label">Visual / Video Prompt</label>
          <textarea
            rows={4}
            value={visualPrompt}
            onChange={(e) => {
              setVisualPrompt(e.target.value);
              markDirty();
            }}
            disabled={shot.is_locked}
            placeholder="Describe camera movement, action, character, and visual tone..."
            style={{ resize: 'vertical' }}
            data-testid="shot-prompt-textarea"
          />
        </div>

        {/* Shot Type & Duration */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="form-group">
            <label className="form-label">Source Type</label>
            <select
              value={shotType}
              onChange={(e) => {
                setShotType(e.target.value as ShotType);
                markDirty();
              }}
              disabled={shot.is_locked}
            >
              <option value="AI_GENERATED">AI GENERATED</option>
              <option value="IMPORTED_VIDEO">IMPORTED VIDEO</option>
              <option value="IMPORTED_IMAGE">IMPORTED IMAGE</option>
              <option value="RECORDED_FOOTAGE">RECORDED FOOTAGE</option>
              <option value="STOCK_ASSET">STOCK ASSET</option>
              <option value="MIXED">MIXED (HYBRID)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Duration (seconds)</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                type="number"
                min="1"
                max="30"
                step="0.5"
                value={durationSeconds}
                onChange={(e) => {
                  setDurationSeconds(Number(e.target.value));
                  markDirty();
                }}
                disabled={shot.is_locked}
              />
              <Clock size={16} color="var(--text-muted)" />
            </div>
          </div>
        </div>

        {/* Subject & Action */}
        <div className="form-group">
          <label className="form-label">Subject & Character Focus</label>
          <input
            type="text"
            value={subject}
            onChange={(e) => {
              setSubject(e.target.value);
              markDirty();
            }}
            disabled={shot.is_locked}
            placeholder="e.g., Lead detective holding torch"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Camera Angle / Movement</label>
          <input
            type="text"
            value={camera}
            onChange={(e) => {
              setCamera(e.target.value);
              markDirty();
            }}
            disabled={shot.is_locked}
            placeholder="e.g., Low angle tracking shot moving right"
          />
        </div>

        {/* Advanced Provider & Inherited Config Toggle */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
          <button
            type="button"
            className="btn btn-xs btn-outline"
            style={{ width: '100%', justifyContent: 'space-between' }}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <span>Advanced Configuration & Inherited Bibles</span>
            {showAdvanced ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>

          {showAdvanced && (
            <div
              style={{
                marginTop: '10px',
                padding: '10px',
                backgroundColor: 'var(--bg-app)',
                borderRadius: '6px',
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                lineHeight: '1.5',
              }}
            >
              <div><strong>Aspect Ratio:</strong> Inherited from project setting</div>
              <div><strong>Provider Routing:</strong> Provider-neutral queue dispatch</div>
              <div><strong>Audit Ledger:</strong> Cost idempotency & reservation enabled</div>
              <div><strong>Lock Integrity:</strong> Enforced by server state machine</div>
            </div>
          )}
        </div>
      </div>

      {/* Drawer Footer */}
      <div
        style={{
          padding: '16px 20px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <button
          className="btn btn-xs btn-outline"
          onClick={async () => {
            if (confirm(`Archive Shot #${shot.shot_number}? Shot record and assets will be safely retained in history.`)) {
              await onDeleteShot(shot.id);
              onClose();
            }
          }}
          disabled={shot.is_locked}
          data-testid="archive-shot-btn"
          title="Archive Shot (Retains history)"
        >
          <Archive size={14} /> Archive
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {saveStatus === 'SAVED' && (
            <span style={{ fontSize: '0.75rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={12} /> All changes saved
            </span>
          )}
          {saveStatus === 'SAVING' && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Saving...
            </span>
          )}
          {saveStatus === 'DIRTY' && (
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-amber)' }}>
              Unsaved changes
            </span>
          )}

          <button
            className="btn btn-primary btn-sm"
            onClick={handleSave}
            disabled={shot.is_locked || saving}
            data-testid="save-shot-btn"
          >
            <Save size={14} /> {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};
