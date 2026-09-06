import React, { useState, useRef } from 'react';
import type { VideoMode, ProjectCreatePayload } from '../../api/types';
import { X, Sparkles, Film, Repeat, Clapperboard, Upload } from 'lucide-react';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (payload: ProjectCreatePayload, file?: File | null) => Promise<void>;
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
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      if (!sourceDocName) {
        setSourceDocName(file.name);
      }
    }
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
          source_document_hint: sourceDocName || selectedFile?.name || undefined,
        },
      };

      if (selectedFile) {
        await onCreate(payload, selectedFile);
      } else {
        await onCreate(payload);
      }
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
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {error && (
              <div className="alert alert-danger" style={{ fontSize: '0.8125rem' }}>
                {error}
              </div>
            )}

            {/* 1. Mode Selection */}
            <div>
              <label className="form-label" style={{ marginBottom: '8px', display: 'block' }}>
                Choose Production Video Mode
              </label>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '10px',
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
                          setTargetPlatform('TikTok / Reels / Shorts');
                        } else if (mode === 'LOOP') {
                          setDurationSeconds(6);
                        } else if (mode === 'STORY') {
                          setAspectRatio('16:9');
                          setDurationSeconds(60);
                          setTargetPlatform('YouTube');
                        }
                      }}
                      style={{
                        padding: '12px 10px',
                        borderRadius: '8px',
                        border: isSelected
                          ? '2px solid var(--primary)'
                          : '1px solid var(--border-default)',
                        backgroundColor: isSelected ? 'rgba(99, 102, 241, 0.1)' : 'var(--bg-card)',
                        cursor: 'pointer',
                        textAlign: 'center',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                      data-testid={`mode-option-${mode.toLowerCase()}`}
                    >
                      {item.icon}
                      <span style={{ fontWeight: 600, fontSize: '0.8125rem' }}>{item.title}</span>
                    </div>
                  );
                })}
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                {modeDescriptions[videoMode].desc}
              </p>
            </div>

            {/* 2. Project Title & Goal */}
            <div className="form-group">
              <label className="form-label">Project Title *</label>
              <input
                type="text"
                required
                placeholder="e.g. Cyberpunk Detective Story Ep. 1"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                data-testid="project-title-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Project Purpose / Logline / Brief</label>
              <textarea
                rows={2}
                placeholder="Describe narrative theme, core message, or target audience..."
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
              />
            </div>

            {/* 3. Specs: Aspect Ratio, Target Duration, Platform, Language */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">Aspect Ratio</label>
                <select
                  value={aspectRatio}
                  onChange={(e) => setAspectRatio(e.target.value)}
                >
                  <option value="16:9">16:9 (Landscape / YouTube)</option>
                  <option value="9:16">9:16 (Vertical / TikTok / Shorts)</option>
                  <option value="1:1">1:1 (Square / Feed)</option>
                  <option value="4:5">4:5 (Portrait)</option>
                  <option value="2.39:1">2.39:1 (Cinematic Anamorphic)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Duration (sec)</label>
                <input
                  type="number"
                  min="3"
                  max="600"
                  value={durationSeconds}
                  onChange={(e) => setDurationSeconds(Number(e.target.value))}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Platform</label>
                <select
                  value={targetPlatform}
                  onChange={(e) => setTargetPlatform(e.target.value)}
                >
                  <option value="YouTube">YouTube</option>
                  <option value="TikTok / Reels / Shorts">TikTok / Shorts / Reels</option>
                  <option value="Instagram">Instagram</option>
                  <option value="Broadcast / Film">Broadcast / Film</option>
                  <option value="Internal / Presentation">Internal / Presentation</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="Thai">Thai (ภาษาไทย)</option>
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
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  placeholder="Paste script title or select reference file..."
                  value={sourceDocName}
                  onChange={(e) => setSourceDocName(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  title="Upload reference document or brief"
                  onClick={() => fileInputRef.current?.click()}
                  data-testid="attach-source-file-btn"
                >
                  <Upload size={14} /> {selectedFile ? 'Attached' : 'Browse File'}
                </button>
              </div>
              {selectedFile && (
                <span style={{ fontSize: '0.75rem', color: '#10b981', marginTop: '4px', display: 'block' }}>
                  ✓ Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
                </span>
              )}
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
