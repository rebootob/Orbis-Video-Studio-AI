import React, { useState } from 'react';
import type { BudgetSummary, CostLedgerEntry } from '../../api/types';
import {
  DollarSign,
  ShieldAlert,
  AlertTriangle,
  FileSpreadsheet,
  Save,
  CheckCircle2,
} from 'lucide-react';

interface BudgetLedgerPanelProps {
  budget: BudgetSummary | null;
  ledgerEntries: CostLedgerEntry[];
  onUpdateBudget: (limit: number | null, threshold: number) => Promise<void>;
}

export const BudgetLedgerPanel: React.FC<BudgetLedgerPanelProps> = ({
  budget,
  ledgerEntries,
  onUpdateBudget,
}) => {
  const [budgetLimit, setBudgetLimit] = useState<string>(
    budget?.budget_limit != null ? String(budget.budget_limit) : ''
  );
  const [threshold, setThreshold] = useState<number>(
    budget?.threshold_percentage || 80.0
  );
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSaveBudget = async () => {
    try {
      setSaving(true);
      const limitVal = budgetLimit.trim() ? parseFloat(budgetLimit) : null;
      await onUpdateBudget(limitVal, threshold);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err: any) {
      alert(`Failed to update budget: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }} data-testid="budget-ledger-panel">
      {/* Alert Banners */}
      {budget?.hard_limit_exceeded && (
        <div className="alert alert-danger" data-testid="hard-budget-alert">
          <ShieldAlert size={20} />
          <div>
            <strong>Hard Budget Limit Exceeded!</strong>
            <p style={{ marginTop: '2px' }}>
              Project committed cost has reached or exceeded the configured limit of $
              {budget.budget_limit?.toFixed(2)} {budget.currency}. All new chargeable generative
              dispatches are blocked.
            </p>
          </div>
        </div>
      )}

      {budget?.soft_limit_exceeded && !budget.hard_limit_exceeded && (
        <div className="alert alert-warning" data-testid="soft-budget-alert">
          <AlertTriangle size={20} />
          <div>
            <strong>Soft Budget Threshold Warning</strong>
            <p style={{ marginTop: '2px' }}>
              Project costs have exceeded {budget.threshold_percentage}% of your limit.
            </p>
          </div>
        </div>
      )}

      {/* Summary Cards Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
        }}
      >
        <div className="card">
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Budget Limit</span>
          <h3 style={{ fontSize: '1.5rem', fontWeight: '700', marginTop: '4px' }}>
            {budget?.budget_limit != null
              ? `$${budget.budget_limit.toFixed(2)}`
              : 'No Limit (Uncapped)'}
          </h3>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            Currency: {budget?.currency || 'USD'}
          </span>
        </div>

        <div className="card">
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Confirmed Spend</span>
          <h3 style={{ fontSize: '1.5rem', fontWeight: '700', marginTop: '4px', color: '#34d399' }}>
            ${budget ? budget.confirmed_cost.toFixed(2) : '0.00'}
          </h3>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            Fully executed provider jobs
          </span>
        </div>

        <div className="card">
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Committed (Total)</span>
          <h3 style={{ fontSize: '1.5rem', fontWeight: '700', marginTop: '4px', color: '#818cf8' }}>
            ${budget ? budget.total_committed_cost.toFixed(2) : '0.00'}
          </h3>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            Estimated + Confirmed reservations
          </span>
        </div>

        <div className="card">
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Remaining Budget</span>
          <h3
            style={{
              fontSize: '1.5rem',
              fontWeight: '700',
              marginTop: '4px',
              color: (budget?.remaining_budget ?? 1) < 0 ? 'var(--accent-rose)' : 'var(--text-primary)',
            }}
          >
            {budget?.remaining_budget != null
              ? `$${budget.remaining_budget.toFixed(2)}`
              : 'Unlimited'}
          </h3>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            Available for new dispatches
          </span>
        </div>
      </div>

      {/* Budget Limit Config Form */}
      <div
        style={{
          backgroundColor: 'var(--bg-panel)',
          padding: '20px',
          borderRadius: '10px',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <DollarSign size={18} color="#818cf8" />
          <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Configure Project Budget Controls</h4>
        </div>

        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 1, minWidth: '200px', marginBottom: 0 }}>
            <label className="form-label">Hard Limit (USD) — Leave empty for uncapped</label>
            <input
              type="number"
              min="0"
              step="1.0"
              placeholder="e.g. 50.00"
              value={budgetLimit}
              onChange={(e) => setBudgetLimit(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ width: '180px', marginBottom: 0 }}>
            <label className="form-label">Soft Warning (%)</label>
            <input
              type="number"
              min="1"
              max="99"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={handleSaveBudget}
            disabled={saving}
            data-testid="save-budget-btn"
          >
            <Save size={14} />
            {saving ? 'Updating...' : 'Save Controls'}
          </button>
        </div>

        {saveSuccess && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.75rem',
              color: '#10b981',
              marginTop: '10px',
            }}
          >
            <CheckCircle2 size={12} /> Budget settings updated successfully
          </span>
        )}
      </div>

      {/* Usage Audit Ledger Table */}
      <div
        style={{
          backgroundColor: 'var(--bg-panel)',
          padding: '20px',
          borderRadius: '10px',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <FileSpreadsheet size={18} color="#818cf8" />
          <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Granular Usage Audit Ledger</h4>
        </div>

        {ledgerEntries.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
            No billable usage records recorded yet for this project.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-default)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '10px 12px' }}>Timestamp</th>
                  <th style={{ padding: '10px 12px' }}>Provider</th>
                  <th style={{ padding: '10px 12px' }}>Operation</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Cost</th>
                </tr>
              </thead>
              <tbody>
                {ledgerEntries.map((entry) => {
                  const isUnknown = entry.cost_status === 'UNKNOWN';
                  const displayCost = isUnknown
                    ? 'UNKNOWN'
                    : `$${(entry.actual_cost ?? entry.estimated_cost ?? 0).toFixed(4)} ${entry.currency}`;

                  return (
                    <tr key={entry.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                        {new Date(entry.created_at).toLocaleString()}
                      </td>
                      <td style={{ padding: '10px 12px', textTransform: 'capitalize' }}>
                        {entry.provider}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        {entry.operation}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            fontWeight: 600,
                            padding: '2px 6px',
                            borderRadius: '3px',
                            backgroundColor:
                              entry.cost_status === 'CONFIRMED'
                                ? 'rgba(16, 185, 129, 0.15)'
                                : entry.cost_status === 'UNKNOWN'
                                ? 'rgba(239, 68, 68, 0.15)'
                                : 'rgba(79, 70, 229, 0.15)',
                            color:
                              entry.cost_status === 'CONFIRMED'
                                ? '#34d399'
                                : entry.cost_status === 'UNKNOWN'
                                ? '#f87171'
                                : '#818cf8',
                          }}
                        >
                          {entry.cost_status}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600 }}>
                        {displayCost}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
