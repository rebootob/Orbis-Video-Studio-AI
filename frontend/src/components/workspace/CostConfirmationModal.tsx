import React, { useEffect, useState } from 'react';
import type { BatchJobEstimateResponse } from '../../api/types';
import { api } from '../../api/client';
import { DollarSign, AlertTriangle, Play, X, ShieldAlert } from 'lucide-react';

interface CostConfirmationModalProps {
  isOpen: boolean;
  projectId: string;
  operationType?: 'CONTINUE_INCOMPLETE' | 'RETRY_FAILED' | 'GENERATE_SELECTED';
  shotIds?: string[] | null;
  onlyIncomplete?: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export const CostConfirmationModal: React.FC<CostConfirmationModalProps> = ({
  isOpen,
  projectId,
  operationType = 'CONTINUE_INCOMPLETE',
  shotIds,
  onlyIncomplete = true,
  onClose,
  onConfirm,
}) => {
  const [loading, setLoading] = useState(false);
  const [estimate, setEstimate] = useState<BatchJobEstimateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dispatching, setDispatching] = useState(false);

  useEffect(() => {
    if (isOpen && projectId) {
      setLoading(true);
      setError(null);
      api
        .estimateBatchJobs(projectId, {
          operation_type: operationType,
          shot_ids: shotIds || undefined,
          only_incomplete: onlyIncomplete,
        })
        .then((res) => {
          setEstimate(res);
        })
        .catch((err) => {
          setError(err.message || 'Failed to estimate batch costs');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [isOpen, projectId, operationType, shotIds, onlyIncomplete]);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    try {
      setDispatching(true);
      await onConfirm();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Dispatch failed');
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} data-testid="cost-confirmation-modal">
      <div
        className="modal-dialog"
        style={{ maxWidth: '520px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DollarSign size={20} color="#818cf8" />
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>
              Pre-Generation Cost Confirmation
            </h3>
          </div>
          <button className="btn btn-xs btn-outline" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary)' }}>
              Calculating generation units and querying pricing rules...
            </div>
          ) : error ? (
            <div className="alert alert-danger" style={{ fontSize: '0.8125rem' }}>
              <ShieldAlert size={16} />
              <span>{error}</span>
            </div>
          ) : estimate ? (
            <>
              {/* Summary Card */}
              <div
                style={{
                  backgroundColor: 'var(--bg-app)',
                  borderRadius: '8px',
                  padding: '16px',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                    Candidate Shots to Generate
                  </div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {estimate.shot_count} {estimate.shot_count === 1 ? 'Shot' : 'Shots'}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                    Estimated Total Cost
                  </div>
                  <div
                    style={{
                      fontSize: '1.5rem',
                      fontWeight: 700,
                      color: estimate.has_unknown_pricing ? 'var(--accent-amber)' : 'var(--text-primary)',
                    }}
                  >
                    {estimate.has_unknown_pricing
                      ? 'UNKNOWN'
                      : estimate.estimated_cost_total !== null && estimate.estimated_cost_total !== undefined
                      ? `$${estimate.estimated_cost_total.toFixed(4)} ${estimate.currency}`
                      : '$0.00'}
                  </div>
                </div>
              </div>

              {/* Warning Messages */}
              {estimate.has_unknown_pricing && (
                <div
                  className="alert alert-warning"
                  style={{ fontSize: '0.8125rem', padding: '10px 12px' }}
                >
                  <AlertTriangle size={16} />
                  <div>
                    <strong>Pricing Status: UNKNOWN</strong>
                    <div style={{ marginTop: '2px', color: 'var(--text-secondary)' }}>
                      Cost pricing is not registered for one or more candidate shots. Pricing will not be fabricated.
                    </div>
                  </div>
                </div>
              )}

              {estimate.warning_messages.map((msg, i) => (
                <div
                  key={i}
                  className="alert alert-warning"
                  style={{ fontSize: '0.8125rem', padding: '10px 12px' }}
                >
                  <AlertTriangle size={16} />
                  <span>{msg}</span>
                </div>
              ))}

              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                Generation jobs will be dispatched asynchronously through the provider adapter queue.
                Costs will be reserved in the project budget ledger and confirmed upon completion.
              </div>
            </>
          ) : null}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={dispatching}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleConfirm}
            disabled={Boolean(loading || dispatching || (estimate && estimate.shot_count === 0))}
            data-testid="confirm-dispatch-btn"
          >
            <Play size={14} />
            {dispatching ? 'Dispatching Jobs...' : 'Confirm & Dispatch'}
          </button>
        </div>
      </div>
    </div>
  );
};
