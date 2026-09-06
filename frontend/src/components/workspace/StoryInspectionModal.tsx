import React from 'react';
import type { Story } from '../../api/types';
import { BookOpen, CheckCircle2, RefreshCw, X, Clock, Globe, Sparkles } from 'lucide-react';

interface StoryInspectionModalProps {
  isOpen: boolean;
  story: Story | null;
  projectTitle?: string;
  projectStatus?: string;
  onClose: () => void;
  onApprove: () => Promise<void>;
  onRegenerate: () => Promise<void>;
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
  if (!isOpen) return null;

  const isApproved = projectStatus === 'STORY_APPROVED' || story?.status === 'APPROVED';

  return (
    <div className="modal-overlay" style={{ zIndex: 1050 }} data-testid="story-inspection-modal">
      <div
        className="modal-content"
        style={{ maxWidth: '680px', width: '90%', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}
      >
        {/* Modal Header */}
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
                Inspect Story Brief & Narrative Outline
              </h3>
            </div>
            {projectTitle && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '26px' }}>
                {projectTitle}
              </div>
            )}
          </div>
          <button className="btn-icon" onClick={onClose} aria-label="Close Story Inspection">
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
          {story ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Status Header */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  backgroundColor: isApproved ? 'rgba(16, 185, 129, 0.1)' : 'rgba(99, 102, 241, 0.1)',
                  border: `1px solid ${isApproved ? 'var(--accent-emerald)' : 'var(--primary)'}`,
                  borderRadius: '6px',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Story Stage Status</div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: isApproved ? 'var(--accent-emerald)' : 'var(--primary)' }}>
                    {isApproved ? 'Story Approved — Ready for Storyboard' : 'Story Generated — Pending Human Review & Approval'}
                  </div>
                </div>
                <span className={`badge ${isApproved ? 'badge-primary' : 'badge-story'}`}>
                  {isApproved ? 'Approved' : 'Review Required'}
                </span>
              </div>

              {/* Title */}
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Story Title
                </label>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {story.title || 'Untitled Story Outline'}
                </div>
              </div>

              {/* Logline */}
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Logline
                </label>
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-default)',
                    padding: '10px 14px',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    lineHeight: '1.5',
                  }}
                >
                  {story.logline || 'No logline available.'}
                </div>
              </div>

              {/* Synopsis */}
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Synopsis / Narrative Arc
                </label>
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-default)',
                    padding: '12px 14px',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    lineHeight: '1.6',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {story.synopsis || 'No synopsis available.'}
                </div>
              </div>

              {/* Specs & Attributes */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                  gap: '10px',
                  paddingTop: '8px',
                }}
              >
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-default)',
                    padding: '8px 12px',
                    borderRadius: '6px',
                  }}
                >
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Sparkles size={12} /> Tone
                  </div>
                  <div style={{ fontWeight: 600, fontSize: '0.8125rem' }}>{story.tone || 'Cinematic'}</div>
                </div>

                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-default)',
                    padding: '8px 12px',
                    borderRadius: '6px',
                  }}
                >
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} /> Target Duration
                  </div>
                  <div style={{ fontWeight: 600, fontSize: '0.8125rem' }}>
                    {story.target_duration_seconds ? `${story.target_duration_seconds}s` : '60s'}
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-default)',
                    padding: '8px 12px',
                    borderRadius: '6px',
                  }}
                >
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Globe size={12} /> Language
                  </div>
                  <div style={{ fontWeight: 600, fontSize: '0.8125rem' }}>{story.language || 'th'}</div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-muted)' }}>
              No story outline record found. Click "Generate Story Brief" to create one.
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '14px 20px',
            borderTop: '1px solid var(--border-default)',
            backgroundColor: 'var(--bg-panel)',
          }}
        >
          <div>
            <button
              className="btn btn-outline btn-sm"
              onClick={onRegenerate}
              title="Regenerate Story Outline"
              data-testid="story-regenerate-btn"
            >
              <RefreshCw size={14} /> Regenerate Story
            </button>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={onClose} data-testid="story-close-btn">
              Close
            </button>
            {!isApproved && story && (
              <button
                className="btn btn-primary"
                onClick={onApprove}
                data-testid="story-approve-btn"
              >
                <CheckCircle2 size={16} /> Approve Story Outline
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
