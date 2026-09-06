import React from 'react';
import type { GenerationJob } from '../../api/types';
import {
  Layers,
  RefreshCw,
  XCircle,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Clock,
  Play,
} from 'lucide-react';

interface GenerationQueuePanelProps {
  jobs: GenerationJob[];
  loading: boolean;
  projectStatus?: string;
  onRefreshJobs: () => Promise<void>;
  onCancelJob: (jobId: string) => Promise<void>;
  onPollJob: (jobId: string) => Promise<void>;
  onRetryJob: (shotId: string) => Promise<void>;
  onResolveReconciliation?: (jobId: string, resolution: string, evidence: string) => Promise<void>;
}

export const GenerationQueuePanel: React.FC<GenerationQueuePanelProps> = ({
  jobs,
  loading,
  projectStatus,
  onRefreshJobs,
  onCancelJob,
  onPollJob,
  onRetryJob,
  onResolveReconciliation,
}) => {
  const [reconcilingJob, setReconcilingJob] = React.useState<GenerationJob | null>(null);
  const [resolution, setResolution] = React.useState<'CONFIRMED_FAILED' | 'CONFIRMED_COMPLETED' | 'CONFIRMED_CANCELLED'>('CONFIRMED_FAILED');
  const [evidence, setEvidence] = React.useState<string>('');
  const [submitting, setSubmitting] = React.useState<boolean>(false);
  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'PENDING':
        return {
          label: 'Queued (Pending)',
          color: '#cbd5e1',
          icon: <Clock size={14} />,
        };
      case 'CLAIMED':
        return {
          label: 'Worker Claimed',
          color: '#60a5fa',
          icon: <RefreshCw size={14} />,
        };
      case 'SUBMITTED':
        return {
          label: 'Submitting to Provider',
          color: '#818cf8',
          icon: <RefreshCw size={14} />,
        };
      case 'POLLING':
        return {
          label: 'Generating Video (Polling)',
          color: '#a78bfa',
          icon: <Play size={14} />,
        };
      case 'COMPLETED':
        return {
          label: 'Completed',
          color: '#34d399',
          icon: <CheckCircle2 size={14} />,
        };
      case 'FAILED':
        return {
          label: 'Failed',
          color: '#f87171',
          icon: <XCircle size={14} />,
        };
      case 'CANCELLED':
        return {
          label: 'Cancelled',
          color: '#94a3b8',
          icon: <XCircle size={14} />,
        };
      case 'RECONCILIATION_REQUIRED':
        return {
          label: 'Reconciliation Required',
          color: '#fbbf24',
          icon: <AlertTriangle size={14} />,
        };
      default:
        return {
          label: status,
          color: '#94a3b8',
          icon: <AlertCircle size={14} />,
        };
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        padding: '20px',
      }}
      data-testid="generation-queue-panel"
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Layers size={20} color="#818cf8" />
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
              Generation Queue & Worker Dispatch
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Real-time monitor of asynchronous video generation tasks and provider polls
            </p>
          </div>
        </div>

        <button
          className="btn btn-sm btn-secondary"
          onClick={onRefreshJobs}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? 'spin-animation' : ''} />
          {loading ? 'Refreshing...' : 'Refresh Queue'}
        </button>
      </div>

      {/* Jobs Table */}
      {jobs.length === 0 ? (
        <div
          style={{
            padding: '48px 20px',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.875rem',
          }}
        >
          No generation jobs have been queued for this project yet.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '0.8125rem',
              textAlign: 'left',
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: '1px solid var(--border-default)',
                  color: 'var(--text-secondary)',
                }}
              >
                <th style={{ padding: '10px 12px' }}>Job ID</th>
                <th style={{ padding: '10px 12px' }}>Shot</th>
                <th style={{ padding: '10px 12px' }}>Status</th>
                <th style={{ padding: '10px 12px' }}>Provider</th>
                <th style={{ padding: '10px 12px' }}>Retries</th>
                <th style={{ padding: '10px 12px' }}>Created</th>
                <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const statusInfo = getStatusDisplay(job.status);
                const isActive = ['PENDING', 'CLAIMED', 'SUBMITTED', 'POLLING'].includes(job.status);
                const isFailed = job.status === 'FAILED';
                const isRecon = job.status === 'RECONCILIATION_REQUIRED';

                return (
                  <tr
                    key={job.id}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      transition: 'background 0.15s ease',
                    }}
                    data-testid={`queue-row-${job.id}`}
                  >
                    <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {job.id.slice(0, 8)}...
                    </td>
                    <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {job.shot_id.slice(0, 8)}...
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          color: statusInfo.color,
                          fontWeight: 500,
                        }}
                      >
                        {statusInfo.icon}
                        {statusInfo.label}
                      </span>
                      {job.error_message && (
                        <div
                          style={{
                            fontSize: '0.7rem',
                            color: 'var(--accent-rose)',
                            marginTop: '4px',
                            maxWidth: '300px',
                          }}
                        >
                          {job.error_message}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px', textTransform: 'capitalize' }}>
                      {job.provider_name}
                    </td>
                    <td style={{ padding: '12px' }}>
                      {job.retries} / {job.max_retries}
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      {new Date(job.created_at).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                        {isActive && (
                          <>
                            <button
                              className="btn btn-xs btn-outline"
                              onClick={() => onPollJob(job.id)}
                              title="Poll Provider Status Now"
                            >
                              <RefreshCw size={12} /> Poll
                            </button>
                            <button
                              className="btn btn-xs btn-danger"
                              onClick={() => onCancelJob(job.id)}
                              title="Cancel Job"
                            >
                              <XCircle size={12} /> Cancel
                            </button>
                          </>
                        )}

                        {isFailed && (() => {
                          const allowedProductionStatuses = [
                            'SHOT_PLAN_APPROVED',
                            'IMAGES_GENERATED',
                            'VIDEO_IN_PROGRESS',
                          ];
                          const isProductionGated = Boolean(projectStatus && !allowedProductionStatuses.includes(projectStatus));
                          return (
                            <button
                              className="btn btn-xs btn-primary"
                              onClick={() => onRetryJob(job.shot_id)}
                              disabled={isProductionGated}
                              title={
                                isProductionGated
                                  ? 'Shot Plan must be approved before retrying production jobs.'
                                  : 'Retry Generation'
                              }
                            >
                              <RefreshCw size={12} /> Retry
                            </button>
                          );
                        })()}

                        {isRecon && (
                          <button
                            className="btn btn-xs btn-outline"
                            data-testid={`reconcile-job-btn-${job.id}`}
                            onClick={() => {
                              setReconcilingJob(job);
                              setResolution('CONFIRMED_FAILED');
                              setEvidence('');
                            }}
                            style={{ color: 'var(--accent-amber)', borderColor: 'var(--accent-amber)' }}
                          >
                            Reconcile
                          </button>
                        )}

                        {job.result_video_url && (
                          <a
                            href={job.result_video_url}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-xs btn-secondary"
                          >
                            Open Video
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Explicit Reconciliation Modal */}
      {reconcilingJob && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          data-testid="reconciliation-modal"
        >
          <div
            style={{
              backgroundColor: 'var(--bg-panel)',
              borderRadius: '12px',
              border: '1px solid var(--border-subtle)',
              padding: '24px',
              width: '480px',
              maxWidth: '90%',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={20} color="#fbbf24" />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Resolve Ambiguous Provider Job</h3>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              This job lost provider synchronization. Choose the verified provider outcome and supply verification evidence.
            </p>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                JOB ID
              </label>
              <div
                style={{
                  fontFamily: 'monospace',
                  fontSize: '0.8rem',
                  padding: '6px 8px',
                  backgroundColor: 'var(--bg-main)',
                  borderRadius: '6px',
                  marginTop: '4px',
                }}
              >
                {reconcilingJob.id}
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                PROVIDER JOB ID
              </label>
              <div
                style={{
                  fontFamily: 'monospace',
                  fontSize: '0.8rem',
                  padding: '6px 8px',
                  backgroundColor: 'var(--bg-main)',
                  borderRadius: '6px',
                  marginTop: '4px',
                }}
              >
                {reconcilingJob.provider_job_id || 'N/A (No provider ID assigned)'}
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                RESOLUTION
              </label>
              <select
                className="input"
                style={{ width: '100%', marginTop: '4px' }}
                value={resolution}
                onChange={(e) => setResolution(e.target.value as any)}
                data-testid="reconciliation-resolution-select"
              >
                <option value="CONFIRMED_FAILED">CONFIRMED_FAILED (Provider failed or never completed)</option>
                <option value="CONFIRMED_COMPLETED">CONFIRMED_COMPLETED (Provider verified completed)</option>
                <option value="CONFIRMED_CANCELLED">CONFIRMED_CANCELLED (Provider verified cancelled)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                VERIFICATION EVIDENCE (Required)
              </label>
              <textarea
                className="input"
                style={{ width: '100%', height: '80px', marginTop: '4px', resize: 'vertical' }}
                placeholder="e.g. Verified via provider dashboard that task timed out and was not billed."
                value={evidence}
                onChange={(e) => setEvidence(e.target.value)}
                data-testid="reconciliation-evidence-input"
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
              <button
                className="btn btn-outline"
                onClick={() => setReconcilingJob(null)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                disabled={submitting || !evidence.trim() || !onResolveReconciliation}
                data-testid="confirm-reconciliation-btn"
                onClick={async () => {
                  if (!onResolveReconciliation || !evidence.trim()) return;
                  setSubmitting(true);
                  try {
                    await onResolveReconciliation(reconcilingJob.id, resolution, evidence.trim());
                    setReconcilingJob(null);
                  } finally {
                    setSubmitting(false);
                  }
                }}
              >
                {submitting ? 'Applying...' : 'Confirm Resolution'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
