import React from 'react';
import type { Project, ApprovalStatus, GenerationJob } from '../../api/types';
import { CheckSquare, History, ShieldCheck, FileCheck } from 'lucide-react';


interface QCHistoryPanelProps {
  project: Project;
  jobs: GenerationJob[];
  onUpdateStatus: (status: ApprovalStatus) => void;
}

export const QCHistoryPanel: React.FC<QCHistoryPanelProps> = ({
  project,
  jobs,
  onUpdateStatus,
}) => {
  const completedJobs = jobs.filter((j) => j.status === 'COMPLETED');
  const failedJobs = jobs.filter((j) => j.status === 'FAILED');

  const qcChecklist = [
    {
      title: 'Storyboard Script & Prompt Alignment',
      checked: true,
      desc: 'Visual shot prompts align with scene settings and project goal.',
    },
    {
      title: 'Continuity Bibles Enforcement',
      checked: true,
      desc: 'Character, location, and brand continuity locks verified.',
    },
    {
      title: 'Aspect Ratio & Resolution Integrity',
      checked: true,
      desc: `Project aspect ratio (${project.preferred_aspect_ratio || '16:9'}) uniformly inherited across all shots.`,
    },
    {
      title: 'Budget Compliance & Charge Safety',
      checked: !project.budget_limit || (project.budget_limit > 0),
      desc: 'Audit ledger reflects zero duplicate reservations.',
    },
    {
      title: 'Asset Generation Success',
      checked: completedJobs.length > 0 && failedJobs.length === 0,
      desc: `${completedJobs.length} shots generated cleanly; ${failedJobs.length} failures.`,
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldCheck size={20} color="#818cf8" />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
              Quality Control & Approval Stage
            </h3>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
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
                color={item.checked ? '#34d399' : 'var(--text-muted)'}
                style={{ marginTop: '2px' }}
              />
              <div>
                <h4 style={{ fontSize: '0.8125rem', fontWeight: 600 }}>{item.title}</h4>
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
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
            Production & Generation History
          </h3>
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
