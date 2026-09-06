import React from 'react';
import { Sparkles, Play, RefreshCw, CheckCircle, CheckSquare, Layers, BookOpen, Film, ArrowRight, AlertTriangle } from 'lucide-react';
import type { OrchestrationStateResponse, AutomationMode } from '../../api/types';

interface AutomationBarProps {
  automationStep: string | null;
  selectedShotCount: number;
  totalShots: number;
  hasFailedJobs: boolean;
  projectStatus?: string;
  videoMode?: string;
  orchestrationState?: OrchestrationStateResponse | null;
  onGenerateFullStoryboard: () => Promise<void>;
  onBatchGenerateShots: () => void; // Opens cost confirmation modal
  onGenerateSelectedShots: () => void; // Opens cost confirmation modal for selected
  onRetryFailed: () => Promise<void>;
  onStageReview?: (stage: 'STORY' | 'STORYBOARD' | 'SHOT_PLAN') => void;
  onExecuteRecommendedAction?: () => Promise<void>;
  onUpdateAutomationMode?: (mode: AutomationMode) => Promise<void>;
}

export const AutomationBar: React.FC<AutomationBarProps> = ({
  automationStep,
  selectedShotCount,
  totalShots,
  hasFailedJobs,
  projectStatus,
  videoMode,
  orchestrationState,
  onGenerateFullStoryboard,
  onBatchGenerateShots,
  onGenerateSelectedShots,
  onRetryFailed,
  onStageReview,
  onExecuteRecommendedAction,
  onUpdateAutomationMode,
}) => {
  const isRunning = Boolean(automationStep);

  // In STORY mode, story outline must be approved before storyboard generation
  const isStoryMode = videoMode === 'STORY';
  const isStoryGated = isStoryMode && projectStatus === 'STORY_GENERATED';

  // Production generation requires SHOT_PLAN_APPROVED or downstream production status
  const allowedProductionStatuses = [
    'SHOT_PLAN_APPROVED',
    'IMAGES_IN_PROGRESS',
    'IMAGES_GENERATED',
    'IMAGES_APPROVED',
    'VIDEO_IN_PROGRESS',
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
        flexDirection: 'column',
        gap: '10px',
        marginBottom: '20px',
      }}
      data-testid="automation-bar"
    >
      {/* Top row: controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          width: '100%',
        }}
      >
        {/* Left: Automation Mode & Batch Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Automation Mode Selector */}
          {onUpdateAutomationMode && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginRight: '4px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)' }}>Mode:</span>
              <select
                data-testid="automation-mode-select"
                className="input-sm"
                value={orchestrationState?.automation_mode || 'MANUAL'}
                onChange={(e) => onUpdateAutomationMode(e.target.value as AutomationMode)}
                style={{
                  fontSize: '0.75rem',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                }}
              >
                <option value="MANUAL">MANUAL</option>
                <option value="ASSISTED">ASSISTED</option>
                <option value="AUTO">AUTO</option>
              </select>
            </div>
          )}

          {/* Recommended Action Button (Primary) */}
          {orchestrationState?.recommended_action && onExecuteRecommendedAction && (
            <button
              className="btn btn-primary"
              onClick={onExecuteRecommendedAction}
              disabled={isRunning || orchestrationState.recommended_action.is_blocked}
              data-testid="orchestration-recommended-action-btn"
              title={
                orchestrationState.recommended_action.blocked_reason ||
                orchestrationState.recommended_action.description
              }
            >
              <ArrowRight size={16} />
              {orchestrationState.recommended_action.display_name}
            </button>
          )}
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

      {/* Blocked Reasons Banner */}
      {orchestrationState?.is_blocked && orchestrationState.blocked_reasons.length > 0 && (
        <div
          data-testid="orchestration-blocked-reasons"
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 12px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '6px',
            color: '#f87171',
            fontSize: '0.75rem',
          }}
        >
          <AlertTriangle size={14} />
          <div>
            <strong>Action Required: </strong>
            {orchestrationState.blocked_reasons.join(' • ')}
          </div>
        </div>
      )}
    </div>
  );
};
