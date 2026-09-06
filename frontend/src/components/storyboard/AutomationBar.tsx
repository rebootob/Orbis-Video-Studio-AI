import React from 'react';
import { Sparkles, Play, RefreshCw, CheckCircle, CheckSquare, Layers, BookOpen, Film } from 'lucide-react';

interface AutomationBarProps {
  automationStep: string | null;
  selectedShotCount: number;
  totalShots: number;
  hasFailedJobs: boolean;
  projectStatus?: string;
  videoMode?: string;
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
  projectStatus,
  videoMode,
  onGenerateFullStoryboard,
  onBatchGenerateShots,
  onGenerateSelectedShots,
  onRetryFailed,
  onStageReview,
}) => {
  const isRunning = Boolean(automationStep);

  // In STORY mode, story outline must be approved before storyboard generation
  const isStoryMode = videoMode === 'STORY';
  const isStoryGated = isStoryMode && projectStatus === 'STORY_GENERATED';

  // Production generation requires SHOT_PLAN_APPROVED or downstream production status
  const allowedProductionStatuses = [
    'SHOT_PLAN_APPROVED',
    'IMAGES_GENERATED',
    'VIDEO_IN_PROGRESS',
    'FINAL_REVIEW',
    'READY_FOR_REVIEW',
    'COMPLETED',
    'APPROVED',
  ];
  const isProductionGated = Boolean(projectStatus && !allowedProductionStatuses.includes(projectStatus));

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
          disabled={isRunning || isStoryGated}
          data-testid="generate-full-storyboard-btn"
          title={
            isStoryGated
              ? 'Story outline must be approved before generating storyboard scenes.'
              : 'Generate visual scenes and layout for the storyboard'
          }
        >
          <Sparkles size={16} />
          {isStoryMode && projectStatus === 'DRAFT'
            ? 'Generate Story Brief'
            : totalShots === 0
            ? 'Generate Storyboard Scenes'
            : 'Regenerate Storyboard Scenes'}
        </button>

        {/* Generate Selected */}
        {selectedShotCount > 0 && (
          <button
            className="btn btn-secondary"
            onClick={onGenerateSelectedShots}
            disabled={isRunning || isProductionGated}
            data-testid="generate-selected-btn"
            title={
              isProductionGated
                ? 'Shot Plan must be approved before generating shots.'
                : 'Generate only selected shots'
            }
          >
            <CheckSquare size={16} /> Generate Selected ({selectedShotCount})
          </button>
        )}

        {/* Batch Generate Incomplete / All */}
        <button
          className="btn btn-outline"
          onClick={onBatchGenerateShots}
          disabled={isRunning || totalShots === 0 || isProductionGated}
          data-testid="batch-generate-shots-btn"
          title={
            isProductionGated
              ? 'Shot Plan must be approved before generating batch video.'
              : 'Review cost estimate and dispatch incomplete shots'
          }
        >
          <Play size={16} /> Batch Generate Video
        </button>

        {hasFailedJobs && (
          <button
            className="btn btn-danger btn-sm"
            onClick={onRetryFailed}
            disabled={isRunning || isProductionGated}
            data-testid="retry-failed-jobs-btn"
            title={
              isProductionGated
                ? 'Shot Plan must be approved before retrying production jobs.'
                : 'Retry failed jobs'
            }
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
