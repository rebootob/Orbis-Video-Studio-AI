import React from 'react';
import type { VideoMode } from '../../api/types';
import { Film, Sparkles, Repeat, Clapperboard, ChevronRight, ArrowRight, CheckCircle2 } from 'lucide-react';

interface ModeSpecBannerProps {
  mode: VideoMode;
  status?: string;
  shotCount?: number;
  completedShotCount?: number;
  onAction?: (action: string) => void;
}

export const ModeSpecBanner: React.FC<ModeSpecBannerProps> = ({
  mode,
  status = 'DRAFT',
  shotCount = 0,
  completedShotCount = 0,
  onAction,
}) => {
  const getModeSpec = () => {
    switch (mode) {
      case 'STORY':
        return {
          icon: <Film size={16} color="#818cf8" />,
          hint: 'Full narrative flow: plans acts, scenes, and shots with continuity bibles.',
        };
      case 'SHORT':
        return {
          icon: <Sparkles size={16} color="#fbbf24" />,
          hint: 'Short mode: optimized for 3-second retention hooks and vertical 9:16 aspect ratio.',
        };
      case 'LOOP':
        return {
          icon: <Repeat size={16} color="#34d399" />,
          hint: 'Loop mode: maintains seamless start/end transitions for ambient & continuous motion.',
        };
      case 'SCENE':
        return {
          icon: <Clapperboard size={16} color="#22d3ee" />,
          hint: 'Scene mode: rapid single-scene visual breakdown into shots.',
        };
    }
  };

  // Staged workflow progression
  const stages = [
    { key: 'STORY', label: 'Story' },
    { key: 'STORYBOARD', label: 'Storyboard' },
    { key: 'SHOT_PLAN', label: 'Shot Plan' },
    { key: 'IMAGES', label: 'Images' },
    { key: 'VIDEO', label: 'Video' },
  ];

  const getActiveStageIndex = (st: string) => {
    const s = st.toUpperCase();
    if (s === 'DRAFT' || s === 'STORY_GENERATED' || s === 'STORY_APPROVED') return 0;
    if (s === 'STORYBOARD_GENERATED' || s === 'STORYBOARD_APPROVED') return 1;
    if (s === 'SHOT_PLAN_GENERATED' || s === 'SHOT_PLAN_APPROVED') return 2;
    if (s === 'IMAGES_GENERATED') return 3;
    if (s === 'VIDEO_IN_PROGRESS' || s === 'FINAL_REVIEW' || s === 'APPROVED' || s === 'COMPLETED') return 4;
    return 1;
  };

  const activeStageIdx = getActiveStageIndex(status);

  // Determine Next Best Action Guidance
  const getNextBestAction = () => {
    const s = status.toUpperCase();
    if (s === 'DRAFT') {
      return {
        action: 'GENERATE_STORY',
        label: 'Generate Story Brief',
        reason: 'Initialize story outline, narrative beats, and scene breakdown from your project prompt.',
        ctaClass: 'btn-primary',
      };
    }
    if (s === 'STORY_GENERATED') {
      return {
        action: 'APPROVE_STORY',
        label: 'Review & Approve Story',
        reason: 'Story brief is ready. Review tone, theme, and acts to approve moving to storyboard.',
        ctaClass: 'btn-primary',
      };
    }
    if (s === 'STORY_APPROVED') {
      return {
        action: 'GENERATE_STORYBOARD',
        label: 'Generate Storyboard',
        reason: 'Story is approved. Generate visual storyboard scenes and shot breakdowns.',
        ctaClass: 'btn-primary',
      };
    }
    if (s === 'STORYBOARD_GENERATED') {
      return {
        action: 'APPROVE_STORYBOARD',
        label: 'Review & Approve Storyboard',
        reason: 'Storyboard scenes populated. Confirm scene structure before detailing shot plan.',
        ctaClass: 'btn-primary',
      };
    }
    if (s === 'STORYBOARD_APPROVED') {
      return {
        action: 'GENERATE_SHOT_PLAN',
        label: 'Finalize Shot Plan',
        reason: 'Storyboard approved. Lock prompts, camera angles, and durations for all planned shots.',
        ctaClass: 'btn-primary',
      };
    }
    if (s === 'SHOT_PLAN_APPROVED' || (shotCount > 0 && completedShotCount < shotCount)) {
      return {
        action: 'BATCH_GENERATE',
        label: 'Estimate & Batch Generate',
        reason: `${shotCount - completedShotCount} shot(s) ready for production. Review cost estimate and dispatch.`,
        ctaClass: 'btn-primary',
      };
    }
    if (s === 'VIDEO_IN_PROGRESS') {
      return {
        action: 'MONITOR_QUEUE',
        label: 'Monitor Generation Queue',
        reason: 'Video generation jobs are actively processing. Check status and inspect ready renders.',
        ctaClass: 'btn-secondary',
      };
    }
    if (s === 'FINAL_REVIEW') {
      return {
        action: 'APPROVE_PROJECT',
        label: 'Complete Final Review & QC',
        reason: 'All shots generated. Inspect QC checklist, verify continuity, and approve completed cut.',
        ctaClass: 'btn-primary',
      };
    }
    if (s === 'COMPLETED') {
      return {
        action: 'VIEW_QC',
        label: 'Project Completed',
        reason: 'All stages approved and full generation history retained.',
        ctaClass: 'btn-secondary',
      };
    }
    return {
      action: 'BATCH_GENERATE',
      label: 'Batch Generate Video',
      reason: 'Continue production for planned shots.',
      ctaClass: 'btn-primary',
    };
  };

  const nextAction = getNextBestAction();
  const spec = getModeSpec();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }} data-testid="mode-spec-banner">
      {/* Top Bar: Mode Hint & Staged Workflow Stepper */}
      <div
        style={{
          backgroundColor: 'var(--bg-panel)',
          borderRadius: '8px',
          padding: '10px 16px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {spec.icon}
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            <strong>{mode} Mode:</strong> {spec.hint}
          </span>
        </div>

        {/* Workflow Stages: Story → Storyboard → Shot Plan → Images → Video */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
          {stages.map((st, idx) => {
            const isPassed = idx < activeStageIdx;
            const isCurrent = idx === activeStageIdx;
            return (
              <React.Fragment key={st.key}>
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    color: isCurrent
                      ? 'var(--primary)'
                      : isPassed
                      ? '#34d399'
                      : 'var(--text-muted)',
                    fontWeight: isCurrent ? 700 : isPassed ? 600 : 400,
                  }}
                >
                  {isPassed && <CheckCircle2 size={11} />}
                  {st.label}
                </span>
                {idx < stages.length - 1 && (
                  <ChevronRight size={12} color="var(--border-default)" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Next Best Action Guidance Banner */}
      <div
        style={{
          backgroundColor: 'rgba(99, 102, 241, 0.08)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          borderRadius: '8px',
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
        data-testid="next-best-action-banner"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '240px' }}>
          <span
            style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--primary)',
              background: 'rgba(99, 102, 241, 0.15)',
              padding: '3px 8px',
              borderRadius: '4px',
            }}
          >
            Recommended Next Step
          </span>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            {nextAction.reason}
          </span>
        </div>

        {onAction && (
          <button
            className={`btn btn-sm ${nextAction.ctaClass}`}
            onClick={() => onAction(nextAction.action)}
            data-testid="next-best-action-btn"
          >
            {nextAction.label} <ArrowRight size={14} />
          </button>
        )}
      </div>
    </div>
  );
};
