import React from 'react';
import type { Project, ApprovalStatus, GenerationJob, BudgetSummary } from '../../api/types';
import { CheckSquare, History, ShieldCheck, FileCheck } from 'lucide-react';

interface QCHistoryPanelProps {
  project: Project;
  jobs: GenerationJob[];
  budget?: BudgetSummary | null;
  onUpdateStatus: (status: ApprovalStatus) => void;
}

export const QCHistoryPanel: React.FC<QCHistoryPanelProps> = ({
  project,
  jobs,
  budget,
  onUpdateStatus,
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

          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {(['DRAFT', 'READY_FOR_REVIEW', 'APPROVED', 'LOCKED', 'NEEDS_ATTENTION'] as ApprovalStatus[]).map((st) => (
              <button
                key={st}
                className={`btn btn-sm ${project.status === st ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onUpdateStatus(st)}
              >
                {st.replace(/_/g, ' ')}
              </button>
            ))}
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
              Generation Dispatch Audit Log & Discovered Assets
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Full historical log of generation dispatches and output assets per shot. Full asset provenance is preserved across retries.
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
    </div>
  );
};
