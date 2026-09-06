import React from 'react';
import type { Project, VideoMode, BudgetSummary, GenerationJob, ApprovalStatus } from '../../api/types';
import { ArrowLeft, DollarSign, Layers, AlertTriangle, ShieldAlert } from 'lucide-react';

interface WorkspaceHeaderProps {
  project: Project;
  budget: BudgetSummary | null;
  jobs: GenerationJob[];
  onBackToDashboard: () => void;
  onUpdateStatus: (status: ApprovalStatus) => void;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({
  project,
  budget,
  jobs,
  onBackToDashboard,
  onUpdateStatus,
}) => {
  const activeJobs = jobs.filter((j) =>
    ['PENDING', 'CLAIMED', 'SUBMITTED', 'POLLING'].includes(j.status)
  );

  const getModeBadge = (mode: VideoMode) => {
    switch (mode) {
      case 'STORY':
        return <span className="badge badge-story">Story Mode</span>;
      case 'SHORT':
        return <span className="badge badge-short">Short Mode</span>;
      case 'LOOP':
        return <span className="badge badge-loop">Loop Mode</span>;
      case 'SCENE':
        return <span className="badge badge-scene">Scene Mode</span>;
    }
  };

  return (
    <header className="app-header" data-testid="workspace-header">
      {/* Left: Back & Project Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button
          className="btn btn-outline btn-sm"
          onClick={onBackToDashboard}
          title="Return to Projects Dashboard"
          data-testid="back-to-dashboard-btn"
        >
          <ArrowLeft size={16} /> Projects
        </button>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: '700',
                color: 'var(--text-primary)',
              }}
            >
              {project.title}
            </h2>
            {getModeBadge(project.video_mode)}
          </div>
          <div
            style={{
              display: 'flex',
              gap: '12px',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              marginTop: '2px',
            }}
          >
            {project.preferred_aspect_ratio && <span>{project.preferred_aspect_ratio}</span>}
            {project.target_duration_seconds && <span>{project.target_duration_seconds}s</span>}
            {project.target_platform && <span>{project.target_platform}</span>}
          </div>
        </div>
      </div>

      {/* Right: Budget Meter, Queue Pill, Approval Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Budget Pill */}
        {budget ? (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '6px',
              backgroundColor: budget.hard_limit_exceeded
                ? 'rgba(239, 68, 68, 0.2)'
                : budget.soft_limit_exceeded
                ? 'rgba(245, 158, 11, 0.2)'
                : 'var(--bg-card)',
              border: `1px solid ${
                budget.hard_limit_exceeded
                  ? 'var(--accent-rose)'
                  : budget.soft_limit_exceeded
                  ? 'var(--accent-amber)'
                  : 'var(--border-default)'
              }`,
              fontSize: '0.8125rem',
            }}
            title={
              budget.hard_limit_exceeded
                ? 'HARD BUDGET LIMIT EXCEEDED - Generative dispatch blocked'
                : budget.soft_limit_exceeded
                ? 'SOFT BUDGET WARNING - Threshold exceeded'
                : 'Project Budget'
            }
            data-testid="budget-meter-pill"
          >
            {budget.hard_limit_exceeded ? (
              <ShieldAlert size={14} color="var(--accent-rose)" />
            ) : budget.soft_limit_exceeded ? (
              <AlertTriangle size={14} color="var(--accent-amber)" />
            ) : (
              <DollarSign size={14} color="#818cf8" />
            )}
            <span>
              ${budget.total_committed_cost.toFixed(2)}
              {budget.budget_limit != null ? ` / $${budget.budget_limit.toFixed(2)}` : ''}{' '}
              {budget.currency}
            </span>
          </div>
        ) : null}

        {/* Queue Status Pill */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '6px',
            backgroundColor: activeJobs.length > 0 ? 'rgba(79, 70, 229, 0.2)' : 'var(--bg-card)',
            border: `1px solid ${
              activeJobs.length > 0 ? 'var(--primary)' : 'var(--border-default)'
            }`,
            fontSize: '0.8125rem',
          }}
          data-testid="queue-status-pill"
        >
          <Layers size={14} color={activeJobs.length > 0 ? '#818cf8' : 'var(--text-muted)'} />
          <span>
            {activeJobs.length > 0 ? `${activeJobs.length} In Queue` : 'Queue Idle'}
          </span>
        </div>

        {/* Approval / QC State Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>
            QC:
          </label>
          <select
            value={project.status}
            onChange={(e) => onUpdateStatus(e.target.value as ApprovalStatus)}
            style={{
              fontSize: '0.75rem',
              padding: '4px 8px',
              fontWeight: 600,
              backgroundColor: 'var(--bg-card)',
            }}
            data-testid="project-status-select"
          >
            <option value="DRAFT">DRAFT</option>
            <option value="READY_FOR_REVIEW">READY FOR REVIEW</option>
            <option value="APPROVED">APPROVED</option>
            <option value="LOCKED">LOCKED</option>
            <option value="NEEDS_ATTENTION">NEEDS ATTENTION</option>
          </select>
        </div>
      </div>
    </header>
  );
};
