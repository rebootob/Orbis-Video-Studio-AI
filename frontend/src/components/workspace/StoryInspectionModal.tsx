import React, { useEffect, useState } from 'react';
import type { Story } from '../../api/types';
import {
  BookOpen,
  CheckCircle2,
  RefreshCw,
  X,
  Clock,
  Globe,
  Sparkles,
  Save,
  Send,
  AlertCircle,
} from 'lucide-react';

interface StoryInspectionModalProps {
  isOpen: boolean;
  story: Story | null;
  projectTitle?: string;
  projectStatus?: string;
  onClose: () => void;
  onApprove: () => Promise<void>;
  onRegenerate: () => Promise<void>;
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function readJson(response: Response) {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Preserve status fallback.
    }
    throw new Error(detail);
  }
  return response.json();
}

export const StoryInspectionModal: React.FC<StoryInspectionModalProps> = ({
  isOpen,
  story,
  projectTitle,
  projectStatus,
  onClose,
  onApprove,
  onRegenerate,
}) => {
  const [workingStory, setWorkingStory] = useState<Story | null>(story);
  const [title, setTitle] = useState(story?.title || projectTitle || '');
  const [logline, setLogline] = useState(story?.logline || '');
  const [synopsis, setSynopsis] = useState(story?.synopsis || '');
  const [tone, setTone] = useState(story?.tone || 'cinematic');
  const [language, setLanguage] = useState(story?.language || 'th');
  const [targetDuration, setTargetDuration] = useState(story?.target_duration_seconds || 60);
  const [saving, setSaving] = useState(false);
  const [manualSubmitted, setManualSubmitted] = useState(false);
  const [manualMessage, setManualMessage] = useState<string | null>(null);
  const [manualError, setManualError] = useState<string | null>(null);

  const workspaceHeader = typeof document !== 'undefined'
    ? document.querySelector<HTMLElement>('[data-testid="workspace-header"]')
    : null;
  const activeProjectId = workingStory?.project_id || story?.project_id || workspaceHeader?.dataset.projectId;
  const automationMode = workspaceHeader?.dataset.automationMode || 'ASSISTED';
  const isManualMode = automationMode === 'MANUAL';

  useEffect(() => {
    if (!isOpen) return;
    setWorkingStory(story);
    setTitle(story?.title || projectTitle || '');
    setLogline(story?.logline || '');
    setSynopsis(story?.synopsis || '');
    setTone(story?.tone || 'cinematic');
    setLanguage(story?.language || 'th');
    setTargetDuration(story?.target_duration_seconds || 60);
    setManualSubmitted(projectStatus === 'STORY_GENERATED');
    setManualMessage(null);
    setManualError(null);
  }, [isOpen, story, projectTitle, projectStatus]);

  useEffect(() => {
    if (!isOpen || !isManualMode || workingStory || !activeProjectId) return;
    let cancelled = false;
    fetch(`${BASE_URL}/projects/${activeProjectId}/story`)
      .then(async (response) => {
        if (response.status === 404) return null;
        return readJson(response);
      })
      .then((loaded: Story | null) => {
        if (cancelled || !loaded) return;
        setWorkingStory(loaded);
        setTitle(loaded.title || projectTitle || '');
        setLogline(loaded.logline || '');
        setSynopsis(loaded.synopsis || '');
        setTone(loaded.tone || 'cinematic');
        setLanguage(loaded.language || 'th');
        setTargetDuration(loaded.target_duration_seconds || 60);
      })
      .catch((err) => {
        if (!cancelled) setManualError(`Unable to load manual Story: ${err.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, isManualMode, workingStory, activeProjectId, projectTitle]);

  if (!isOpen) return null;

  const isApproved = projectStatus === 'STORY_APPROVED' || workingStory?.status === 'APPROVED';
  const isSubmitted = manualSubmitted || projectStatus === 'STORY_GENERATED' || workingStory?.status === 'GENERATED';
  const canManualEdit = isManualMode && projectStatus === 'DRAFT' && !isSubmitted && !workingStory?.is_locked;

  const validateManualStory = () => {
    if (!title.trim()) return 'Story title is required.';
    if (!logline.trim() && !synopsis.trim()) return 'Enter at least a Logline or Synopsis.';
    if (!activeProjectId) return 'Active project context is unavailable. Close and reopen the workspace.';
    return null;
  };

  const saveManualStory = async (): Promise<Story> => {
    const validationError = validateManualStory();
    if (validationError) throw new Error(validationError);
    setSaving(true);
    setManualError(null);
    try {
      const response = await fetch(`${BASE_URL}/projects/${activeProjectId}/story/manual`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          logline: logline.trim() || null,
          synopsis: synopsis.trim() || null,
          tone: tone.trim() || null,
          target_duration_seconds: Number(targetDuration),
          language: language.trim() || 'th',
        }),
      });
      const saved = (await readJson(response)) as Story;
      setWorkingStory(saved);
      setManualMessage('Manual Story saved — CreativeProvider was not called.');
      return saved;
    } finally {
      setSaving(false);
    }
  };

  const handleSaveManual = async () => {
    try {
      await saveManualStory();
    } catch (err: any) {
      setManualError(err.message || 'Manual Story save failed.');
    }
  };

  const handleSubmitManual = async () => {
    try {
      await saveManualStory();
      const response = await fetch(`${BASE_URL}/projects/${activeProjectId}/orchestration/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'SUBMIT_MANUAL_STORY' }),
      });
      await readJson(response);
      setManualSubmitted(true);
      setWorkingStory((current) => current ? { ...current, status: 'GENERATED' } : current);
      setManualMessage('Manual Story submitted for human review — zero CreativeProvider calls.');
    } catch (err: any) {
      setManualError(err.message || 'Manual Story submission failed.');
    }
  };

  const shownStory = workingStory || story;

  return (
    <div className="modal-overlay" style={{ zIndex: 1050 }} data-testid="story-inspection-modal">
      <div
        className="modal-content"
        style={{ maxWidth: '760px', width: '92%', maxHeight: '88vh', display: 'flex', flexDirection: 'column' }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-default)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen size={18} color="var(--primary)" />
              <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600 }}>
                {canManualEdit ? 'Manual Story / Script Editor' : 'Inspect Story Brief & Narrative Outline'}
              </h3>
            </div>
            {projectTitle && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '26px' }}>
                {projectTitle} {isManualMode ? '• MANUAL' : `• ${automationMode}`}
              </div>
            )}
          </div>
          <button className="btn-icon" onClick={onClose} aria-label="Close Story Inspection">
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
          {(shownStory || canManualEdit) ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  backgroundColor: isApproved
                    ? 'rgba(16, 185, 129, 0.1)'
                    : isSubmitted
                    ? 'rgba(99, 102, 241, 0.1)'
                    : 'rgba(245, 158, 11, 0.08)',
                  border: `1px solid ${isApproved ? 'var(--accent-emerald)' : isSubmitted ? 'var(--primary)' : 'var(--accent-amber)'}`,
                  borderRadius: '6px',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Story Stage Status</div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                    {isApproved
                      ? 'Story Approved — Ready for Storyboard'
                      : isSubmitted
                      ? 'Story Submitted — Pending Human Review & Approval'
                      : isManualMode
                      ? 'Manual Draft — Edit and submit when ready'
                      : 'Story Generated — Pending Human Review & Approval'}
                  </div>
                </div>
                <span className={`badge ${isApproved ? 'badge-primary' : 'badge-story'}`}>
                  {isApproved ? 'Approved' : isSubmitted ? 'Review Required' : 'Draft'}
                </span>
              </div>

              {manualError && (
                <div className="alert alert-danger" style={{ fontSize: '0.8125rem' }}>
                  <AlertCircle size={14} /> {manualError}
                </div>
              )}
              {manualMessage && (
                <div className="alert alert-success" style={{ fontSize: '0.8125rem' }}>
                  <CheckCircle2 size={14} /> {manualMessage}
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Story Title</label>
                {canManualEdit ? (
                  <input value={title} onChange={(e) => setTitle(e.target.value)} data-testid="manual-story-title-input" />
                ) : (
                  <div style={{ fontSize: '1rem', fontWeight: 600 }}>{shownStory?.title || 'Untitled Story Outline'}</div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Logline</label>
                {canManualEdit ? (
                  <textarea
                    rows={2}
                    value={logline}
                    onChange={(e) => setLogline(e.target.value)}
                    placeholder="One-sentence story premise..."
                    data-testid="manual-story-logline-input"
                  />
                ) : (
                  <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-default)', padding: '10px 14px', borderRadius: '6px', fontSize: '0.875rem', lineHeight: '1.5' }}>
                    {shownStory?.logline || 'No logline available.'}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Synopsis / Narrative Arc / Script Notes</label>
                {canManualEdit ? (
                  <textarea
                    rows={8}
                    value={synopsis}
                    onChange={(e) => setSynopsis(e.target.value)}
                    placeholder="Paste or write your Story / Script / narrative outline here..."
                    data-testid="manual-story-synopsis-input"
                  />
                ) : (
                  <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-default)', padding: '12px 14px', borderRadius: '6px', fontSize: '0.875rem', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                    {shownStory?.synopsis || 'No synopsis available.'}
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
                <div className="form-group">
                  <label className="form-label"><Sparkles size={12} /> Tone</label>
                  {canManualEdit ? (
                    <input value={tone} onChange={(e) => setTone(e.target.value)} />
                  ) : (
                    <div style={{ fontWeight: 600, fontSize: '0.8125rem' }}>{shownStory?.tone || 'Cinematic'}</div>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label"><Clock size={12} /> Target Duration</label>
                  {canManualEdit ? (
                    <input type="number" min="1" max="600" value={targetDuration} onChange={(e) => setTargetDuration(Number(e.target.value))} />
                  ) : (
                    <div style={{ fontWeight: 600, fontSize: '0.8125rem' }}>{shownStory?.target_duration_seconds ? `${shownStory.target_duration_seconds}s` : '60s'}</div>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label"><Globe size={12} /> Language</label>
                  {canManualEdit ? (
                    <input value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="th" />
                  ) : (
                    <div style={{ fontWeight: 600, fontSize: '0.8125rem' }}>{shownStory?.language || 'th'}</div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-muted)' }}>
              No story outline record found. {isManualMode ? 'Switch to DRAFT to author it manually.' : 'Click "Generate Story Brief" to create one.'}
            </div>
          )}
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '10px',
            padding: '14px 20px',
            borderTop: '1px solid var(--border-default)',
            backgroundColor: 'var(--bg-panel)',
          }}
        >
          <div style={{ display: 'flex', gap: '8px' }}>
            {canManualEdit ? (
              <>
                <button className="btn btn-outline btn-sm" onClick={handleSaveManual} disabled={saving} data-testid="manual-story-save-btn">
                  <Save size={14} /> {saving ? 'Saving...' : 'Save Manual Story'}
                </button>
                <button className="btn btn-primary btn-sm" onClick={handleSubmitManual} disabled={saving} data-testid="manual-story-submit-btn">
                  <Send size={14} /> Save & Submit for Review
                </button>
              </>
            ) : !isManualMode && (
              <button className="btn btn-outline btn-sm" onClick={onRegenerate} title="Regenerate Story Outline" data-testid="story-regenerate-btn">
                <RefreshCw size={14} /> Regenerate Story
              </button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={onClose} data-testid="story-close-btn">Close</button>
            {!isApproved && (isSubmitted || (!isManualMode && shownStory)) && (
              <button className="btn btn-primary" onClick={onApprove} data-testid="story-approve-btn">
                <CheckCircle2 size={16} /> Approve Story Outline
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};