import React from 'react';
import { Sparkles, Play, RefreshCw, CheckCircle } from 'lucide-react';

interface AutomationBarProps {
  automationStep: string | null;
  onGenerateFullStoryboard: () => Promise<void>;
  onBatchGenerateShots: () => Promise<void>;
  onRetryFailed: () => Promise<void>;
  hasFailedJobs: boolean;
  totalShots: number;
}

export const AutomationBar: React.FC<AutomationBarProps> = ({
  automationStep,
  onGenerateFullStoryboard,
  onBatchGenerateShots,
  onRetryFailed,
  hasFailedJobs,
  totalShots,
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
      {/* Left: High-Level Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <button
          className="btn btn-primary"
          onClick={onGenerateFullStoryboard}
          disabled={isRunning}
          data-testid="generate-full-storyboard-btn"
          title="Automated orchestration: Creates Story, Plans Scenes, and Generates Shot Prompts"
        >
          <Sparkles size={16} />
          {totalShots === 0 ? 'Create Full Storyboard (Auto)' : 'Regenerate Full Storyboard'}
        </button>

        <button
          className="btn btn-secondary"
          onClick={onBatchGenerateShots}
          disabled={isRunning || totalShots === 0}
          data-testid="batch-generate-shots-btn"
          title="Queue generation for all eligible unlocked AI shots in the project"
        >
          <Play size={16} /> Batch Generate All Shots
        </button>

        {hasFailedJobs && (
          <button
            className="btn btn-danger btn-sm"
            onClick={onRetryFailed}
            disabled={isRunning}
            data-testid="retry-failed-jobs-btn"
          >
            <RefreshCw size={14} /> Retry Failed Jobs
          </button>
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
