import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BudgetLedgerPanel } from '../components/budget/BudgetLedgerPanel';
import type { BudgetSummary, CostLedgerEntry } from '../api/types';

describe('BudgetLedgerPanel', () => {
  it('displays soft limit warning when soft limit is exceeded', () => {
    const budget: BudgetSummary = {
      project_id: 'proj-1',
      budget_limit: 100,
      currency: 'USD',
      threshold_percentage: 80,
      confirmed_cost: 85,
      estimated_cost: 0,
      total_committed_cost: 85,
      remaining_budget: 15,
      soft_limit_exceeded: true,
      hard_limit_exceeded: false,
      has_unknown_costs: false,
    };

    render(
      <BudgetLedgerPanel
        budget={budget}
        ledgerEntries={[]}
        onUpdateBudget={vi.fn()}
      />
    );

    expect(screen.getByTestId('soft-budget-alert')).toBeInTheDocument();
    expect(screen.queryByTestId('hard-budget-alert')).not.toBeInTheDocument();
  });

  it('displays hard limit error when hard limit is exceeded', () => {
    const budget: BudgetSummary = {
      project_id: 'proj-1',
      budget_limit: 50,
      currency: 'USD',
      threshold_percentage: 80,
      confirmed_cost: 55,
      estimated_cost: 0,
      total_committed_cost: 55,
      remaining_budget: -5,
      soft_limit_exceeded: true,
      hard_limit_exceeded: true,
      has_unknown_costs: false,
    };

    render(
      <BudgetLedgerPanel
        budget={budget}
        ledgerEntries={[]}
        onUpdateBudget={vi.fn()}
      />
    );

    expect(screen.getByTestId('hard-budget-alert')).toBeInTheDocument();
    expect(screen.getByText(/All new chargeable generative dispatches are blocked/i)).toBeInTheDocument();
  });

  it('renders UNKNOWN cost in ledger table without fabricating prices', () => {
    const budget: BudgetSummary = {
      project_id: 'proj-1',
      budget_limit: null,
      currency: 'USD',
      confirmed_cost: 0,
      estimated_cost: 0,
      total_committed_cost: 0,
      soft_limit_exceeded: false,
      hard_limit_exceeded: false,
      has_unknown_costs: true,
    };

    const entries: CostLedgerEntry[] = [
      {
        id: 'led-1',
        project_id: 'proj-1',
        provider: 'vidu',
        operation: 'video_generation',
        currency: 'USD',
        cost_status: 'UNKNOWN',
        created_at: new Date().toISOString(),
      },
    ];

    render(
      <BudgetLedgerPanel
        budget={budget}
        ledgerEntries={entries}
        onUpdateBudget={vi.fn()}
      />
    );

    expect(screen.getAllByText('UNKNOWN').length).toBeGreaterThanOrEqual(1);
  });
});

