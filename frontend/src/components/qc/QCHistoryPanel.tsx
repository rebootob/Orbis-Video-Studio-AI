import React, { useState, useEffect } from 'react';
import type { Project, ApprovalStatus, GenerationJob, BudgetSummary, OrchestrationAuditResponse, QCRun, ApprovalRecord } from '../../api/types';
import { apiClient } from '../../api/client';
import { CheckSquare, History, ShieldCheck, FileCheck, GitCommit, ChevronLeft, ChevronRight, Award, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

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
  const [qcRuns, setQcRuns] = useState<QCRun[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [qcTotal, setQcTotal] = useState<number>(0);
  const [qcOffset, setQcOffset] = useState<number>(0);
  const qcLimit = 10;
  const [loadingQcHistory, setLoadingQcHistory] = useState<boolean>(false);

  const fetchQCHistory = async () => {
    setLoadingQcHistory(true);
    try {
      if (apiClient && typeof apiClient.getQCHistory === 'function') {
        const res = await apiClient.getQCHistory(project.id, qcOffset, qcLimit);
        setQcRuns(res?.qc_runs || []);
        setApprovals(res?.approvals || []);
        setQcTotal(res?.total_count || 0);
      }
    } catch (err) {
      console.error('Failed to fetch QC history:', err);
    } finally {
      setLoadingQcHistory(false);
    }
  };

  useEffect(() => {
    fetchQCHistory();
  }, [project.id, qcOffset]);

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

      {/* QC Audit & Warning Decision Log */}
      <div
        style={{
          backgroundColor: 'var(--bg-panel)',
          borderRadius: '10px',
          border: '1px solid var(--border-subtle)',
          padding: '20px',
        }}
        data-testid="qc-runs-history-card"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Award size={20} color="#818cf8" />
            <div>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
                QC Evaluations & Warning Decisions History
              </h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Historical audit trail of auto QC runs, warning decisions with actor reasons, and release approvals.
              </p>
            </div>
          </div>

          {/* Pagination Controls */}
          {qcTotal > qcLimit && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => setQcOffset(Math.max(0, qcOffset - qcLimit))}
                disabled={qcOffset === 0 || loadingQcHistory}
                style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-button)', color: 'var(--text-primary)', cursor: qcOffset === 0 ? 'not-allowed' : 'pointer' }}
                data-testid="qc-history-prev-page"
              >
                <ChevronLeft size={16} />
              </button>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {qcOffset + 1}-{Math.min(qcOffset + qcLimit, qcTotal)} of {qcTotal}
              </span>
              <button
                onClick={() => setQcOffset(qcOffset + qcLimit)}
                disabled={qcOffset + qcLimit >= qcTotal || loadingQcHistory}
                style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-button)', color: 'var(--text-primary)', cursor: qcOffset + qcLimit >= qcTotal ? 'not-allowed' : 'pointer' }}
                data-testid="qc-history-next-page"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </div>

        {/* Approvals Summary */}
        {approvals.length > 0 && (
          <div style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <h4 style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#22c55e', margin: 0 }}>
              Release Approvals ({approvals.length})
            </h4>
            {approvals.map((appr) => (
              <div key={appr.id} style={{ padding: '10px 14px', borderRadius: '6px', backgroundColor: 'rgba(34, 197, 94, 0.08)', border: '1px solid rgba(34, 197, 94, 0.2)', fontSize: '0.8125rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>Approved Cut v{appr.timeline_version} by {appr.approved_by}</strong>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {new Date(appr.created_at).toLocaleString()}
                  </span>
                </div>
                {appr.notes && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                    Notes: {appr.notes}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Past QC Runs */}
        {loadingQcHistory ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
            Loading QC audit log...
          </div>
        ) : qcRuns.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
            No past QC runs recorded for this project.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }} data-testid="qc-runs-list">
            {qcRuns.map((run) => (
              <div
                key={run.id}
                style={{
                  padding: '14px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {run.status === 'PASSED' ? (
                      <CheckCircle2 size={16} color="#22c55e" />
                    ) : run.status === 'BLOCKED' ? (
                      <XCircle size={16} color="#ef4444" />
                    ) : (
                      <AlertTriangle size={16} color="#eab308" />
                    )}
                    <strong>QC Run (Revision v{run.timeline_version})</strong>
                    <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', fontWeight: 600, backgroundColor: run.status === 'PASSED' ? 'rgba(34, 197, 94, 0.15)' : run.status === 'BLOCKED' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(234, 179, 8, 0.15)', color: run.status === 'PASSED' ? '#22c55e' : run.status === 'BLOCKED' ? '#ef4444' : '#eab308' }}>
                      {run.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    Actor: {run.actor} • {new Date(run.created_at).toLocaleString()}
                  </div>
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', gap: '12px', marginBottom: '8px' }}>
                  <span>Blockers: {run.blocker_count}</span>
                  <span>Warnings: {run.warning_count}</span>
                  <span>Decisions: {run.decisions?.length || 0}</span>
                </div>

                {/* Warning Decisions */}
                {run.decisions && run.decisions.length > 0 && (
                  <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-tertiary)' }}>Recorded Warning Decisions:</div>
                    {run.decisions.map((dec) => (
                      <div key={dec.id} style={{ fontSize: '0.75rem', padding: '6px 10px', borderRadius: '4px', backgroundColor: 'var(--bg-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                        <div>
                          <span style={{ fontWeight: 600, color: dec.decision === 'ACCEPTED_WITH_REASON' ? '#22c55e' : '#ef4444' }}>
                            {dec.decision}:
                          </span>{' '}
                          {dec.reason || 'No reason provided'}
                        </div>
                        <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          by {dec.actor} at {new Date(dec.decided_at).toLocaleTimeString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
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
