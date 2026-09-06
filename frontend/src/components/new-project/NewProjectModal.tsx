import React, { useState } from 'react';
import type { VideoMode, ProjectCreatePayload } from '../../api/types';
import { X, Sparkles, Film, Repeat, Clapperboard, FileText, CheckCircle2 } from 'lucide-react';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (payload: ProjectCreatePayload) => Promise<void>;
}

export const NewProjectModal: React.FC<NewProjectModalProps> = ({ isOpen, onClose, onCreate }) => {
  const [videoMode, setVideoMode] = useState<VideoMode>('STORY');
  const [title, setTitle] = useState('');
  const [purpose, setPurpose] = useState('');
  const [targetPlatform, setTargetPlatform] = useState('YouTube');
  const [durationSeconds, setDurationSeconds] = useState<number>(30);
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [language, setLanguage] = useState('English');
  const [automationLevel, setAutomationLevel] = useState<'AUTO' | 'ASSISTED' | 'MANUAL'>('AUTO');
  const [sourceDocName, setSourceDocName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const modeDescriptions: Record<VideoMode, { title: string; desc: string; icon: React.ReactNode }> = {
    STORY: {
      title: 'Story Mode',
      desc: 'Narrative arc: Story → Scene acts → Visual shots. Best for cinematic scripts and episodic content.',
      icon: <Film size={20} color="#818cf8" />,
    },
    SHORT: {
      title: 'Short Mode',
      desc: 'High-impact hook, rapid pacing, and viral payoff. Best for TikTok, Reels, and Shorts.',
      icon: <Sparkles size={20} color="#fbbf24" />,
    },
    LOOP: {
      title: 'Loop Mode',
      desc: 'Seamless continuous background or ambient loop with matched start/end frames.',
      icon: <Repeat size={20} color="#34d399" />,
    },
    SCENE: {
      title: 'Scene Mode',
      desc: 'Focused single-scene breakdown into shots without requiring full narrative story acts.',
      icon: <Clapperboard size={20} color="#22d3ee" />,
    },
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Project title is required.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const payload: ProjectCreatePayload = {
        title: title.trim(),
        video_mode: videoMode,
        purpose: purpose.trim() || undefined,
        target_platform: targetPlatform,
        target_duration_seconds: durationSeconds > 0 ? durationSeconds : undefined,
        preferred_aspect_ratio: aspectRatio,
        mode_config: {
          automation_level: automationLevel,
          language: language,
          source_document_hint: sourceDocName || undefined,
        },
      };

      await onCreate(payload);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} data-testid="new-project-modal">
      <div
        className="modal-dialog"
        style={{ maxWidth: '640px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} color="#818cf8" />
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600' }}>New Video Project</h2>
          </div>
          <button className="btn btn-xs btn-outline" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="alert alert-danger">{error}</div>}

            {/* 1. Mode Selection */}
            <div className="form-group">
              <label className="form-label">Video Production Mode</label>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '12px',
                  marginTop: '4px',
                }}
              >
                {(['STORY', 'SHORT', 'LOOP', 'SCENE'] as VideoMode[]).map((mode) => {
                  const item = modeDescriptions[mode];
                  const isSelected = videoMode === mode;
                  return (
                    <div
                      key={mode}
                      onClick={() => {
                        setVideoMode(mode);
                        if (mode === 'SHORT') {
                          setAspectRatio('9:16');
                          setDurationSeconds(15);
                        } else if (mode === 'LOOP') {
                          setDurationSeconds(5);
                        } else if (mode === 'STORY') {
                          setAspectRatio('16:9');
                          setDurationSeconds(60);
                        }
                      }}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        border: isSelected
                          ? '2px solid var(--primary)'
                          : '1px solid var(--border-default)',
                        backgroundColor: isSelected
                          ? 'rgba(79, 70, 229, 0.1)'
                          : 'var(--bg-input)',
                        transition: 'all 0.15s ease',
                      }}
                      data-testid={`mode-option-${mode.toLowerCase()}`}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          marginBottom: '6px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {item.icon}
                          <span style={{ fontWeight: '600', fontSize: '0.875rem' }}>
                            {item.title}
                          </span>
                        </div>
                        {isSelected && <CheckCircle2 size={16} color="var(--primary)" />}
                      </div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.3' }}>
                        {item.desc}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 2. Project Title & Goal */}
            <div className="form-group">
              <label className="form-label">Project Title *</label>
              <input
                type="text"
                placeholder="e.g., Cyberpunk Detective Chase"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                data-testid="project-title-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Purpose / Creative Goal</label>
              <input
                type="text"
                placeholder="e.g., Commercial trailer showcasing hero product in dramatic lighting"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
              />
            </div>

            {/* 3. Specs Row: Platform, Duration, Aspect Ratio */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
              <div className="form-group">
                <label className="form-label">Platform</label>
                <select
                  value={targetPlatform}
                  onChange={(e) => setTargetPlatform(e.target.value)}
                >
                  <option value="YouTube">YouTube</option>
                  <option value="TikTok">TikTok</option>
                  <option value="Instagram Reels">Instagram Reels</option>
                  <option value="Cinema">Cinema</option>
                  <option value="Web">Web / Landing Page</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Duration (s)</label>
                <input
                  type="number"
                  min="1"
                  max="600"
                  value={durationSeconds}
                  onChange={(e) => setDurationSeconds(Number(e.target.value))}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Aspect Ratio</label>
                <select
                  value={aspectRatio}
                  onChange={(e) => setAspectRatio(e.target.value)}
                >
                  <option value="16:9">16:9 (Landscape)</option>
                  <option value="9:16">9:16 (Vertical)</option>
                  <option value="1:1">1:1 (Square)</option>
                  <option value="4:5">4:5 (Social)</option>
                  <option value="2.39:1">2.39:1 (Anamorphic)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="English">English</option>
                  <option value="Spanish">Spanish</option>
                  <option value="French">French</option>
                  <option value="German">German</option>
                  <option value="Japanese">Japanese</option>
                  <option value="Chinese">Chinese</option>
                </select>
              </div>
            </div>


            {/* 4. Automation Level */}
            <div className="form-group">
              <label className="form-label">Automation Level (Default: AUTO)</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                {[
                  {
                    level: 'AUTO',
                    desc: 'Full Storyboard & Shots generated automatically with one click',
                  },
                  {
                    level: 'ASSISTED',
                    desc: 'System outlines scenes; you refine shots with AI assistance',
                  },
                  {
                    level: 'MANUAL',
                    desc: 'You create each scene and shot individually',
                  },
                ].map((item) => (
                  <button
                    key={item.level}
                    type="button"
                    className={`btn btn-sm ${
                      automationLevel === item.level ? 'btn-primary' : 'btn-secondary'
                    }`}
                    style={{ flex: 1, padding: '8px' }}
                    onClick={() => setAutomationLevel(item.level as any)}
                  >
                    {item.level}
                  </button>
                ))}
              </div>
              <span className="form-hint" style={{ marginTop: '4px' }}>
                {automationLevel === 'AUTO' && '⭐ Recommended: Generates complete storyboards with zero manual friction.'}
                {automationLevel === 'ASSISTED' && 'AI plans structure, while allowing step-by-step review before generation.'}
                {automationLevel === 'MANUAL' && 'Full per-shot control without automatic story generation.'}
              </span>
            </div>

            {/* 5. Document Ingestion Entry Point */}
            <div className="form-group">
              <label className="form-label">Source Context / Document (Optional)</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  placeholder="Paste script title or brief notes..."
                  value={sourceDocName}
                  onChange={(e) => setSourceDocName(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  title="Upload reference document"
                  onClick={() => alert('Document ingestion ready. Additional documents can also be uploaded in the References tab.')}
                >
                  <FileText size={16} /> Attach
                </button>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
              data-testid="submit-create-project-btn"
            >
              {submitting ? 'Creating Project...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
