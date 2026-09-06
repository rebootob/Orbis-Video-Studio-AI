import React from 'react';
import type { Project, ApprovalStatus, GenerationJob, BudgetSummary, OrchestrationAuditResponse } from '../../api/types';
import { CheckSquare, History, ShieldCheck, FileCheck, GitCommit } from 'lucide-react';

interface QCHistoryPanelProps {
  project: Project;
  jobs: GenerationJob[];
  budget?: BudgetSummary | null;
  orchestrationAudits?: OrchestrationAuditResponse[];
  onUpdateStatus?: (status: ApprovalStatus) => void;
  onApproveStage?: (stage: string) => Promise<void>;
}

export const QCHistoryPanel: React.FC<QCHistoryPanelProps> = ({
  project,
  jobs,
  budget,
  orchestrationAudits,
  onUpdateStatus,
  onApproveStage,
}) => {
  const completedJobs = jobs.filter((j) => j.status === 'COMPLETED');
  const failedJobs = jobs.filter((j) => j.status === 'FAILED');

  const qcChecklist = [
    {
      title: 'Budget Compliance & Hard Limit Check',
      isAutomated: true,
      passed: !budget?.hard_limit_exceeded,
      statusLabel: budget?.hard_limit_exceeded ? 'FAIL: Hard Limit Exceeded' : 'PASS: Within Budget Limit',
      desc: budget?.hard_limit_exceeded
        ? 'Current commitments exceed hard budget limit. Dispatch is blocked.'
        : `Confirmed cost $${budget?.confirmed_cost?.toFixed(2) || '0.00'} / Limit $${project.budget_limit ?? 'None'}.`,
    },
    {
      title: 'Asset Generation Reliability Check',
      isAutomated: true,
      passed: completedJobs.length > 0 && failedJobs.length === 0,
      statusLabel:
        failedJobs.length > 0
          ? `${failedJobs.length} Failed Job(s)`
          : completedJobs.length > 0
          ? `${completedJobs.length} Completed`
          : 'Pending Generation',
      desc: `${completedJobs.length} job(s) completed successfully, ${failedJobs.length} failed.`,
    },
    {
      title: 'Aspect Ratio & Resolution Consistency',
      isAutomated: true,
      passed: Boolean(project.preferred_aspect_ratio),
      statusLabel: project.preferred_aspect_ratio || 'Configured',
      desc: `Target aspect ratio: ${project.preferred_aspect_ratio || '16:9'} assigned to project.`,
    },
    {
      title: 'Storyboard Script & Prompt Creative Review',
      isAutomated: false,
      passed: false,
      statusLabel: 'Manual Review Required',
      desc: 'Editorial check: verify that visual shot prompts align with creative vision.',
    },
    {
      title: 'Continuity Bibles & Character Review',
      isAutomated: false,
      passed: false,
      statusLabel: 'Manual Review Required',
      desc: 'Creative check: inspect character appearance and location continuity across generated shots.',
    },
  ];

  const handleApprove = (stage: string) => {
    if (onApproveStage) {
      onApproveStage(stage);
    } else if (onUpdateStatus) {
      onUpdateStatus(stage as ApprovalStatus);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }} data-testid="qc-history-panel">
      {/* Approval Status Card */}
      <div
        style={{
          backgroundColor: 'var(--bg-panel)',
          borderRadius: '10px',
          border: '1px solid var(--border-subtle)',
          padding: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldCheck size={20} color="#818cf8" />
            <div>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
                Quality Control & Approval Stage
              </h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Stage gates and pre-release verification checklist
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Current Stage:</span>
            <span className="badge badge-primary" style={{ fontSize: '0.75rem', padding: '4px 8px' }}>
              {project.status.replace(/_/g, ' ')}
            </span>

            {project.status === 'STORY_GENERATED' && (
              <button
                className="btn btn-sm btn-primary"
                onClick={() => handleApprove('STORY_APPROVED')}
                data-testid="qc-approve-story-btn"
              >
                Approve Story & Proceed
              </button>
            )}
            {project.status === 'STORYBOARD_GENERATED' && (
              <button
                className="btn btn-sm btn-primary"
                onClick={() => handleApprove('STORYBOARD_APPROVED')}
                data-testid="qc-approve-storyboard-btn"
              >
                Approve Storyboard & Proceed
              </button>
            )}
            {project.status === 'SHOT_PLAN_GENERATED' && (
              <button
                className="btn btn-sm btn-primary"
                onClick={() => handleApprove('SHOT_PLAN_APPROVED')}
                data-testid="qc-approve-shot-plan-btn"
              >
                Approve Shot Plan & Proceed
              </button>
            )}
            {project.status === 'FINAL_REVIEW' && (
              <button
                className="btn btn-sm btn-primary"
                onClick={() => handleApprove('APPROVED')}
                data-testid="qc-approve-final-cut-btn"
              >
                Approve Final Cut
              </button>
            )}
            {project.status === 'APPROVED' && (
              <button
                className="btn btn-sm btn-primary"
                onClick={() => handleApprove('COMPLETED')}
                data-testid="qc-complete-project-btn"
              >
                Mark Completed
              </button>
            )}
          </div>
        </div>

        {/* QC Checklist */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {qcChecklist.map((item, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '10px 14px',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <CheckSquare
                size={16}
                color={
                  item.isAutomated
                    ? item.passed
                      ? '#34d399'
                      : 'var(--accent-rose)'
                    : 'var(--accent-amber)'
                }
                style={{ marginTop: '2px' }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h4 style={{ fontSize: '0.8125rem', fontWeight: 600 }}>{item.title}</h4>
                  <span
                    className={`badge ${
                      item.isAutomated
                        ? item.passed
                          ? 'badge-approved'
                          : 'badge-attention'
                        : 'badge-review'
                    }`}
                    style={{ fontSize: '0.65rem' }}
                  >
                    {item.statusLabel}
                  </span>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  {item.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Generation History & Discoverability */}
      <div
        style={{
          backgroundColor: 'var(--bg-panel)',
          borderRadius: '10px',
          border: '1px solid var(--border-subtle)',
          padding: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <History size={20} color="#818cf8" />
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
              Generation Dispatch Audit Log
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Audit log of dispatched generation jobs and output assets for this project.
            </p>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
            No generation activity logged yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {jobs.map((job) => (
              <div
                key={job.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.8125rem',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileCheck size={14} color="#818cf8" />
                    <strong>Job {job.id.slice(0, 8)}...</strong>
                    <span className="badge badge-draft" style={{ fontSize: '0.65rem' }}>
                      {job.provider_name}
                    </span>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        color:
                          job.status === 'COMPLETED'
                            ? '#34d399'
                            : job.status === 'FAILED'
                            ? '#f87171'
                            : '#818cf8',
                      }}
                    >
                      {job.status}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Shot ID: {job.shot_id} • Dispatched:{' '}
                    {new Date(job.created_at).toLocaleString()}
                  </div>
                </div>

                {job.result_video_url ? (
                  <a
                    href={job.result_video_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-xs btn-primary"
                  >
                    View Asset
                  </a>
                ) : (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    No media URL
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Orchestration State Machine Audit History */}
      <div
        style={{
          backgroundColor: 'var(--bg-panel)',
          borderRadius: '10px',
          border: '1px solid var(--border-subtle)',
          padding: '20px',
        }}
        data-testid="orchestration-history-card"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <GitCommit size={20} color="#818cf8" />
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
              Orchestration Stage Transition Audit History
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Append-only state machine transitions, human approvals, and guard verifications.
            </p>
          </div>
        </div>

        {!orchestrationAudits || orchestrationAudits.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
            No stage transitions recorded yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }} data-testid="orchestration-audit-history">
            {orchestrationAudits.map((item) => (
              <div
                key={item.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.75rem',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <strong>{item.action}</strong>
                    <span className="badge badge-primary" style={{ fontSize: '0.65rem' }}>
                      {item.from_state} &rarr; {item.to_state || item.from_state}
                    </span>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        color: item.result === 'APPLIED' ? '#34d399' : item.result === 'NO_OP' ? 'var(--text-muted)' : '#f87171',
                      }}
                    >
                      {item.result}
                    </span>
                  </div>
                  {item.detail && (
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {item.detail}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                  <div>Actor: {item.actor}</div>
                  <div>{new Date(item.created_at).toLocaleTimeString()}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
