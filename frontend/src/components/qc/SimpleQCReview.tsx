import React, { useState, useEffect } from 'react';
import type { QCSimpleSummary, QCRun, QCFinding, WarningDecisionType } from '../../api/types';
import { apiClient } from '../../api/client';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Info,
  RefreshCw,
  Award,
  Check,
  X,
  MessageSquare
} from 'lucide-react';

interface SimpleQCReviewProps {
  projectId: string;
  onApprovalComplete?: () => void;
}

export const SimpleQCReview: React.FC<SimpleQCReviewProps> = ({
  projectId,
  onApprovalComplete,
}) => {
  const [summary, setSummary] = useState<QCSimpleSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [runningQC, setRunningQC] = useState<boolean>(false);
  const [approving, setApproving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);

  // Warning decision modal state
  const [selectedFinding, setSelectedFinding] = useState<QCFinding | null>(null);
  const [decisionType, setDecisionType] = useState<WarningDecisionType>('ACCEPTED_WITH_REASON');
  const [reasonText, setReasonText] = useState<string>('');
  const [submittingDecision, setSubmittingDecision] = useState<boolean>(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  // Approval notes state
  const [approvalNotes, setApprovalNotes] = useState<string>('');

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getQCSummary(projectId);
      setSummary(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load QC summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [projectId]);

  const handleRunQC = async () => {
    setRunningQC(true);
    setError(null);
    try {
      await apiClient.runQC(projectId);
      await fetchSummary();
    } catch (err: any) {
      setError(err?.message || 'Failed to execute QC run');
    } finally {
      setRunningQC(false);
    }
  };

  const handleOpenDecisionModal = (finding: QCFinding) => {
    setSelectedFinding(finding);
    setDecisionType('ACCEPTED_WITH_REASON');
    setReasonText('');
    setDecisionError(null);
  };

  const handleCloseDecisionModal = () => {
    setSelectedFinding(null);
    setReasonText('');
    setDecisionError(null);
  };

  const handleSubmitDecision = async () => {
    if (!selectedFinding) return;

    if (decisionType === 'ACCEPTED_WITH_REASON' && !reasonText.trim()) {
      setDecisionError('A non-empty text reason is required to accept a QC warning.');
      return;
    }

    setSubmittingDecision(true);
    setDecisionError(null);
    try {
      await apiClient.recordWarningDecision(
        projectId,
        selectedFinding.id,
        decisionType,
        reasonText.trim()
      );
      handleCloseDecisionModal();
      await fetchSummary();
    } catch (err: any) {
      setDecisionError(err?.message || 'Failed to submit warning decision');
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    setError(null);
    try {
      await apiClient.approveProduction(projectId, {
        notes: approvalNotes.trim() || undefined,
      });
      await fetchSummary();
      if (onApprovalComplete) {
        onApprovalComplete();
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to approve production stage');
    } finally {
      setApproving(false);
    }
  };

  const latestRun: QCRun | null | undefined = summary?.latest_qc_run;
  const findings: QCFinding[] = latestRun?.findings || [];
  const decisionsMap = new Map<string, string>(
    (latestRun?.decisions || []).map((d) => [d.finding_id, d.decision])
  );

  const blockers = findings.filter((f) => f.severity === 'BLOCKER');
  const warnings = findings.filter((f) => f.severity === 'WARNING');
  const infos = findings.filter((f) => f.severity === 'INFO');

  const getStatusBadge = () => {
    if (!summary?.has_active_qc) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '16px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8' }}>
          <RefreshCw size={14} /> Evaluation Required
        </span>
      );
    }

    const status = latestRun?.status;
    if (status === 'PASSED') {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '16px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'rgba(34, 197, 94, 0.15)', color: '#22c55e' }}>
          <CheckCircle2 size={14} /> Passed Clean
        </span>
      );
    }
    if (status === 'WARNINGS_PENDING') {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '16px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'rgba(234, 179, 8, 0.15)', color: '#eab308' }}>
          <AlertTriangle size={14} /> Warnings Pending Review
        </span>
      );
    }
    if (status === 'BLOCKED') {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '16px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>
          <XCircle size={14} /> Blocked by Issues
        </span>
      );
    }
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '16px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'rgba(99, 102, 241, 0.15)', color: '#6366f1' }}>
        <RefreshCw size={14} className="animate-spin" /> In Progress
      </span>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }} data-testid="simple-qc-review">
      {/* Header & Status Card */}
      <div style={{ backgroundColor: 'var(--bg-panel)', borderRadius: '10px', border: '1px solid var(--border-subtle)', padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <ShieldCheck size={24} color="#818cf8" />
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>
                Quality Control & Approval Gate
              </h2>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                {summary?.summary_message || 'Automated pre-release quality check'}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {getStatusBadge()}
            <button
              onClick={handleRunQC}
              disabled={runningQC || loading}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-button)',
                color: 'var(--text-primary)',
                fontSize: '0.875rem',
                fontWeight: 500,
                cursor: runningQC || loading ? 'not-allowed' : 'pointer',
              }}
              data-testid="run-qc-btn"
            >
              <RefreshCw size={16} className={runningQC ? 'animate-spin' : ''} />
              {runningQC ? 'Evaluating...' : 'Run Auto QC'}
            </button>
          </div>
        </div>

        {error && (
          <div style={{ marginTop: '16px', padding: '12px', borderRadius: '6px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        {/* Counter Pills */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '16px', flexWrap: 'wrap' }}>
          <div style={{ padding: '8px 14px', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', fontSize: '0.8125rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Blockers: </span>
            <strong style={{ color: (summary?.blocker_count || 0) > 0 ? '#ef4444' : 'var(--text-primary)' }}>
              {summary?.blocker_count ?? 0}
            </strong>
          </div>

          <div style={{ padding: '8px 14px', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', fontSize: '0.8125rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Pending Warnings: </span>
            <strong style={{ color: (summary?.pending_warning_count || 0) > 0 ? '#eab308' : 'var(--text-primary)' }}>
              {summary?.pending_warning_count ?? 0}
            </strong>
          </div>

          <div style={{ padding: '8px 14px', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', fontSize: '0.8125rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Accepted Warnings: </span>
            <strong style={{ color: '#22c55e' }}>
              {summary?.accepted_warning_count ?? 0}
            </strong>
          </div>
        </div>
      </div>

      {/* Findings List */}
      {summary?.has_active_qc && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Blockers Section */}
          {blockers.length > 0 && (
            <div style={{ backgroundColor: 'var(--bg-panel)', borderRadius: '10px', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444', fontWeight: 600, fontSize: '0.9375rem', marginBottom: '12px' }}>
                <XCircle size={18} />
                <span>Blocking Issues ({blockers.length}) — Must be resolved before approval</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {blockers.map((finding) => (
                  <div key={finding.id} style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.2)' }} data-testid={`finding-${finding.id}`}>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#ef4444' }}>
                      {finding.target_label ? `[${finding.target_label}] ` : ''}{finding.message}
                    </div>
                    {finding.why_it_matters && (
                      <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                        <strong>Why it matters:</strong> {finding.why_it_matters}
                      </p>
                    )}
                    {finding.recommended_fix && (
                      <p style={{ fontSize: '0.8125rem', color: '#6366f1', margin: '4px 0 0 0' }}>
                        <strong>Recommended fix:</strong> {finding.recommended_fix}
                      </p>
                    )}
                    {showTechnicalDetails && (
                      <div style={{ marginTop: '8px', fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>
                        Rule: {finding.rule_code} | Target ID: {finding.target_id || 'N/A'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings Section */}
          {warnings.length > 0 && (
            <div style={{ backgroundColor: 'var(--bg-panel)', borderRadius: '10px', border: '1px solid rgba(234, 179, 8, 0.3)', padding: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#eab308', fontWeight: 600, fontSize: '0.9375rem', marginBottom: '12px' }}>
                <AlertTriangle size={18} />
                <span>Warnings Requiring Review ({warnings.length})</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {warnings.map((finding) => {
                  const decision = decisionsMap.get(finding.id);
                  const isAccepted = decision === 'ACCEPTED_WITH_REASON';
                  const isFixRequired = decision === 'FIX_REQUIRED';

                  return (
                    <div key={finding.id} style={{ padding: '12px', borderRadius: '8px', backgroundColor: isAccepted ? 'rgba(34, 197, 94, 0.05)' : 'rgba(234, 179, 8, 0.05)', border: `1px solid ${isAccepted ? 'rgba(34, 197, 94, 0.2)' : 'rgba(234, 179, 8, 0.2)'}` }} data-testid={`finding-${finding.id}`}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                            {finding.target_label ? `[${finding.target_label}] ` : ''}{finding.message}
                          </div>
                          {finding.why_it_matters && (
                            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                              <strong>Why it matters:</strong> {finding.why_it_matters}
                            </p>
                          )}
                          {finding.recommended_fix && (
                            <p style={{ fontSize: '0.8125rem', color: '#6366f1', margin: '4px 0 0 0' }}>
                              <strong>Recommended fix:</strong> {finding.recommended_fix}
                            </p>
                          )}
                          {showTechnicalDetails && (
                            <div style={{ marginTop: '8px', fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>
                              Rule: {finding.rule_code} | Target ID: {finding.target_id || 'N/A'}
                            </div>
                          )}
                        </div>

                        <div>
                          {isAccepted ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'rgba(34, 197, 94, 0.15)', color: '#22c55e' }}>
                              <Check size={14} /> Accepted
                            </span>
                          ) : isFixRequired ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>
                              <X size={14} /> Fix Required
                            </span>
                          ) : (
                            <button
                              onClick={() => handleOpenDecisionModal(finding)}
                              style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #eab308', backgroundColor: 'rgba(234, 179, 8, 0.1)', color: '#eab308', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                              data-testid={`decide-btn-${finding.id}`}
                            >
                              Review & Decide
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Info Section */}
          {infos.length > 0 && (
            <div style={{ backgroundColor: 'var(--bg-panel)', borderRadius: '10px', border: '1px solid var(--border-subtle)', padding: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#818cf8', fontWeight: 600, fontSize: '0.9375rem', marginBottom: '12px' }}>
                <Info size={18} />
                <span>Informational Findings ({infos.length})</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {infos.map((finding) => (
                  <div key={finding.id} style={{ padding: '10px', borderRadius: '6px', backgroundColor: 'var(--bg-subtle)', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    <div>{finding.message}</div>
                    {showTechnicalDetails && (
                      <div style={{ marginTop: '4px', fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>
                        Rule: {finding.rule_code} | Target ID: {finding.target_id || 'N/A'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Technical Details Toggle */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', border: 'none', background: 'transparent', color: 'var(--text-tertiary)', fontSize: '0.75rem', cursor: 'pointer' }}
          data-testid="toggle-tech-details"
        >
          {showTechnicalDetails ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          {showTechnicalDetails ? 'Hide Technical Details' : 'Show Technical Details'}
        </button>
      </div>

      {/* Final Approval Action Card */}
      <div style={{ backgroundColor: 'var(--bg-panel)', borderRadius: '10px', border: '1px solid var(--border-subtle)', padding: '20px' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Award size={18} color="#22c55e" />
          Final Production Approval
        </h3>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '0 0 16px 0' }}>
          Once approved, the current timeline revision is locked as official release history. Any subsequent timeline edits will create a new revision requiring fresh QC review.
        </p>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '4px' }}>
            Approval Notes / Release Remarks (Optional)
          </label>
          <input
            type="text"
            value={approvalNotes}
            onChange={(e) => setApprovalNotes(e.target.value)}
            placeholder="e.g., Final director cut approved for distribution"
            style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-input)', color: 'var(--text-primary)', fontSize: '0.875rem' }}
          />
        </div>

        <button
          onClick={handleApprove}
          disabled={!summary?.can_approve || approving}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            width: '100%',
            padding: '12px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: summary?.can_approve ? '#22c55e' : 'var(--bg-button-disabled)',
            color: summary?.can_approve ? '#ffffff' : 'var(--text-disabled)',
            fontSize: '0.9375rem',
            fontWeight: 600,
            cursor: summary?.can_approve && !approving ? 'pointer' : 'not-allowed',
          }}
          data-testid="approve-production-btn"
        >
          <Award size={18} />
          {approving ? 'Approving Production...' : 'Approve Final Production Cut'}
        </button>
      </div>

      {/* Warning Decision Modal */}
      {selectedFinding && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} data-testid="warning-decision-modal">
          <div style={{ backgroundColor: 'var(--bg-panel)', borderRadius: '12px', border: '1px solid var(--border-subtle)', width: '100%', maxWidth: '500px', padding: '24px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <MessageSquare size={20} color="#eab308" /> Review Warning Finding
              </h3>
              <button onClick={handleCloseDecisionModal} style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'rgba(234, 179, 8, 0.08)', border: '1px solid rgba(234, 179, 8, 0.2)', marginBottom: '16px' }}>
              <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{selectedFinding.message}</div>
              {selectedFinding.why_it_matters && (
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {selectedFinding.why_it_matters}
                </p>
              )}
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Decision
              </label>
              <div style={{ display: 'flex', gap: '12px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="decisionType"
                    value="ACCEPTED_WITH_REASON"
                    checked={decisionType === 'ACCEPTED_WITH_REASON'}
                    onChange={() => setDecisionType('ACCEPTED_WITH_REASON')}
                  />
                  Accept Warning with Reason
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="decisionType"
                    value="FIX_REQUIRED"
                    checked={decisionType === 'FIX_REQUIRED'}
                    onChange={() => setDecisionType('FIX_REQUIRED')}
                  />
                  Require Fix
                </label>
              </div>
            </div>

            {decisionType === 'ACCEPTED_WITH_REASON' && (
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Justification Reason (Mandatory) <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <textarea
                  rows={3}
                  value={reasonText}
                  onChange={(e) => setReasonText(e.target.value)}
                  placeholder="Explain why this warning is acceptable for release..."
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-input)', color: 'var(--text-primary)', fontSize: '0.875rem' }}
                  data-testid="warning-reason-input"
                />
              </div>
            )}

            {decisionError && (
              <div style={{ marginBottom: '16px', padding: '10px', borderRadius: '6px', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', fontSize: '0.8125rem' }}>
                {decisionError}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={handleCloseDecisionModal}
                style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-button)', color: 'var(--text-primary)', cursor: 'pointer' }}
              >
                Cancel
              </button>

              <button
                onClick={handleSubmitDecision}
                disabled={submittingDecision}
                style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', backgroundColor: '#6366f1', color: '#ffffff', fontWeight: 600, cursor: submittingDecision ? 'not-allowed' : 'pointer' }}
                data-testid="submit-decision-btn"
              >
                {submittingDecision ? 'Submitting...' : 'Save Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
