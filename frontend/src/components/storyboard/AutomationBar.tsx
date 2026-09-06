import React from 'react';
import { Sparkles, Play, RefreshCw, CheckCircle, CheckSquare, Layers, BookOpen, Film } from 'lucide-react';

interface AutomationBarProps {
  automationStep: string | null;
  selectedShotCount: number;
  totalShots: number;
  hasFailedJobs: boolean;
  onGenerateFullStoryboard: () => Promise<void>;
  onBatchGenerateShots: () => void; // Opens cost confirmation modal
  onGenerateSelectedShots: () => void; // Opens cost confirmation modal for selected
  onRetryFailed: () => Promise<void>;
  onStageReview?: (stage: 'STORY' | 'STORYBOARD' | 'SHOT_PLAN') => void;
}

export const AutomationBar: React.FC<AutomationBarProps> = ({
  automationStep,
  selectedShotCount,
  totalShots,
  hasFailedJobs,
  onGenerateFullStoryboard,
  onBatchGenerateShots,
  onGenerateSelectedShots,
  onRetryFailed,
  onStageReview,
}) => {
  const isRunning = Boolean(automationStep);

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '8px',
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '20px',
      }}
      data-testid="automation-bar"
    >
      {/* Left: High-Level Automation & Batch Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        <button
          className="btn btn-primary"
          onClick={onGenerateFullStoryboard}
          disabled={isRunning}
          data-testid="generate-full-storyboard-btn"
          title="Generate visual scenes and layout for the storyboard"
        >
          <Sparkles size={16} />
          {totalShots === 0 ? 'Generate Storyboard Scenes' : 'Regenerate Storyboard Scenes'}
        </button>

        {/* Generate Selected */}
        {selectedShotCount > 0 && (
          <button
            className="btn btn-secondary"
            onClick={onGenerateSelectedShots}
            disabled={isRunning}
            data-testid="generate-selected-btn"
            title="Generate only selected shots"
          >
            <CheckSquare size={16} /> Generate Selected ({selectedShotCount})
          </button>
        )}

        {/* Batch Generate Incomplete / All */}
        <button
          className="btn btn-outline"
          onClick={onBatchGenerateShots}
          disabled={isRunning || totalShots === 0}
          data-testid="batch-generate-shots-btn"
          title="Review cost estimate and dispatch incomplete shots"
        >
          <Play size={16} /> Batch Generate Video
        </button>

        {hasFailedJobs && (
          <button
            className="btn btn-danger btn-sm"
            onClick={onRetryFailed}
            disabled={isRunning}
            data-testid="retry-failed-jobs-btn"
          >
            <RefreshCw size={14} /> Retry Failed
          </button>
        )}

        {/* Stage Inspection shortcuts */}
        {onStageReview && (
          <div style={{ display: 'flex', gap: '4px', marginLeft: '6px' }}>
            <button
              className="btn btn-xs btn-outline"
              onClick={() => onStageReview('STORY')}
              title="Inspect Story Brief & Narrative Outline"
              data-testid="review-stage-story-btn"
            >
              <BookOpen size={12} /> Inspect Story
            </button>
            <button
              className="btn btn-xs btn-outline"
              onClick={() => onStageReview('STORYBOARD')}
              title="Inspect Storyboard Scenes & Layout"
              data-testid="review-stage-storyboard-btn"
            >
              <Layers size={12} /> Inspect Storyboard
            </button>
            <button
              className="btn btn-xs btn-outline"
              onClick={() => onStageReview('SHOT_PLAN')}
              title="Inspect Shot Plan & Prompts"
              data-testid="review-stage-shot-plan-btn"
            >
              <Film size={12} /> Inspect Shot Plan
            </button>
          </div>
        )}
      </div>

      {/* Right: Progress / Status Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem' }}>
        {isRunning ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: '#818cf8',
              fontWeight: 500,
            }}
          >
            <RefreshCw size={14} className="spin-animation" style={{ animation: 'spin 1s linear infinite' }} />
            <span>{automationStep}</span>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
            <CheckCircle size={14} color="#10b981" />
            <span>Ready ({totalShots} shots planned)</span>
          </div>
        )}
      </div>
    </div>
  );
};
