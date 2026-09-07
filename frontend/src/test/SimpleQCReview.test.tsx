import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { SimpleQCReview } from '../components/qc/SimpleQCReview';
import { apiClient } from '../api/client';
import type { QCSimpleSummary, QCRun } from '../api/types';

vi.mock('../api/client', () => {
  const mockApiClient = {
    getQCSummary: vi.fn(),
    runQC: vi.fn(),
    recordWarningDecision: vi.fn(),
    approveProduction: vi.fn(),
  };
  return {
    apiClient: mockApiClient,
    api: mockApiClient,
  };
});

describe('SimpleQCReview Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('Test 17: Default simple UX hides technical details/IDs and shows clean status summary', async () => {
    const mockRun: QCRun = {
      id: 'qc-run-uuid-12345',
      project_id: 'proj-uuid-67890',
      timeline_id: 'timeline-uuid-11111',
      timeline_version: 1,
      status: 'PASSED',
      blocker_count: 0,
      warning_count: 0,
      info_count: 0,
      actor: 'system',
      created_at: '2026-09-07T00:00:00Z',
      findings: [
        {
          id: 'finding-1',
          project_id: 'proj-uuid-67890',
          qc_run_id: 'qc-run-uuid-12345',
          timeline_id: 'timeline-uuid-11111',
          rule_code: 'TECHNICAL_RULE_CODE_MISSING_VISUAL',
          severity: 'INFO',
          message: 'All visuals match canonical specifications.',
          target_id: 'target-uuid-99999',
          created_at: '2026-09-07T00:00:00Z',
        },
      ],
      decisions: [],
    };

    const mockSummary: QCSimpleSummary = {
      project_id: 'proj-uuid-67890',
      active_timeline_id: 'timeline-uuid-11111',
      active_timeline_version: 1,
      active_timeline_status: 'DRAFT',
      latest_qc_run: mockRun,
      has_active_qc: true,
      can_approve: true,
      blocker_count: 0,
      pending_warning_count: 0,
      accepted_warning_count: 0,
      summary_message: 'Timeline revision v1 evaluated clean. Ready for final approval.',
    };

    vi.mocked(apiClient.getQCSummary).mockResolvedValue(mockSummary);

    render(<SimpleQCReview projectId="proj-uuid-67890" />);

    await waitFor(() => {
      expect(screen.getByText('Quality Control & Approval Gate')).toBeInTheDocument();
    });

    // Verify clean high-level message is displayed
    expect(screen.getByText('Timeline revision v1 evaluated clean. Ready for final approval.')).toBeInTheDocument();
    expect(screen.getByText('Passed Clean')).toBeInTheDocument();

    // Technical rule code and target ID must NOT be visible by default
    expect(screen.queryByText(/TECHNICAL_RULE_CODE_MISSING_VISUAL/)).not.toBeInTheDocument();
    expect(screen.queryByText(/target-uuid-99999/)).not.toBeInTheDocument();

    // Expand technical details
    const toggleBtn = screen.getByTestId('toggle-tech-details');
    fireEvent.click(toggleBtn);

    // Technical details become visible when explicitly expanded
    await waitFor(() => {
      expect(screen.getByText(/Rule: TECHNICAL_RULE_CODE_MISSING_VISUAL/)).toBeInTheDocument();
    });
  });

  it('Test 18: Accepting warning without text reason fails validation, non-empty reason succeeds', async () => {
    const mockRun: QCRun = {
      id: 'qc-run-uuid-1',
      project_id: 'proj-1',
      timeline_id: 'tl-1',
      timeline_version: 1,
      status: 'RUNNING',
      blocker_count: 0,
      warning_count: 1,
      info_count: 0,
      actor: 'system',
      created_at: '2026-09-07T00:00:00Z',
      findings: [
        {
          id: 'finding-warning-1',
          project_id: 'proj-1',
          qc_run_id: 'qc-run-uuid-1',
          timeline_id: 'tl-1',
          rule_code: 'UNVERIFIED_VISUAL_CONTINUITY',
          severity: 'WARNING',
          message: 'Visual continuity between shots cannot be deterministically verified.',
          created_at: '2026-09-07T00:00:00Z',
        },
      ],
      decisions: [],
    };

    const mockSummary: QCSimpleSummary = {
      project_id: 'proj-1',
      active_timeline_id: 'tl-1',
      active_timeline_version: 1,
      active_timeline_status: 'DRAFT',
      latest_qc_run: mockRun,
      has_active_qc: true,
      can_approve: false,
      blocker_count: 0,
      pending_warning_count: 1,
      accepted_warning_count: 0,
      summary_message: 'QC evaluation has 1 warning requiring explicit user decision.',
    };

    vi.mocked(apiClient.getQCSummary).mockResolvedValue(mockSummary);

    render(<SimpleQCReview projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByTestId('decide-btn-finding-warning-1')).toBeInTheDocument();
    });

    // Open decision modal
    fireEvent.click(screen.getByTestId('decide-btn-finding-warning-1'));

    await waitFor(() => {
      expect(screen.getByTestId('warning-decision-modal')).toBeInTheDocument();
    });

    // Click Save Decision with empty reason text
    fireEvent.click(screen.getByTestId('submit-decision-btn'));

    await waitFor(() => {
      expect(screen.getByText('A non-empty text reason is required to accept a QC warning.')).toBeInTheDocument();
    });
    expect(apiClient.recordWarningDecision).not.toHaveBeenCalled();

    // Provide non-empty reason text
    const reasonInput = screen.getByTestId('warning-reason-input');
    fireEvent.change(reasonInput, { target: { value: 'Director intended creative jump cut' } });

    vi.mocked(apiClient.recordWarningDecision).mockResolvedValue({
      id: 'dec-1',
      project_id: 'proj-1',
      qc_run_id: 'qc-run-uuid-1',
      timeline_id: 'tl-1',
      finding_id: 'finding-warning-1',
      decision: 'ACCEPTED_WITH_REASON',
      reason: 'Director intended creative jump cut',
      actor: 'user',
      decided_at: '2026-09-07T00:00:00Z',
    });

    fireEvent.click(screen.getByTestId('submit-decision-btn'));

    await waitFor(() => {
      expect(apiClient.recordWarningDecision).toHaveBeenCalledWith(
        'proj-1',
        'finding-warning-1',
        'ACCEPTED_WITH_REASON',
        'Director intended creative jump cut'
      );
    });
  });

  it('Test 19: Blocker findings strictly disable approval button and prevent bypassing', async () => {
    const mockRun: QCRun = {
      id: 'qc-run-blocked',
      project_id: 'proj-1',
      timeline_id: 'tl-1',
      timeline_version: 1,
      status: 'BLOCKED',
      blocker_count: 1,
      warning_count: 0,
      info_count: 0,
      actor: 'system',
      created_at: '2026-09-07T00:00:00Z',
      findings: [
        {
          id: 'finding-blocker-1',
          project_id: 'proj-1',
          qc_run_id: 'qc-run-blocked',
          timeline_id: 'tl-1',
          rule_code: 'MISSING_VISUAL',
          severity: 'BLOCKER',
          message: 'Shot placement has no visual asset assigned.',
          why_it_matters: 'Every shot placement requires a visual asset.',
          recommended_fix: 'Generate or select a visual asset.',
          created_at: '2026-09-07T00:00:00Z',
        },
      ],
      decisions: [],
    };

    const mockSummary: QCSimpleSummary = {
      project_id: 'proj-1',
      active_timeline_id: 'tl-1',
      active_timeline_version: 1,
      active_timeline_status: 'DRAFT',
      latest_qc_run: mockRun,
      has_active_qc: true,
      can_approve: false,
      blocker_count: 1,
      pending_warning_count: 0,
      accepted_warning_count: 0,
      summary_message: 'Timeline revision v1 is blocked by 1 blocker issue.',
    };

    vi.mocked(apiClient.getQCSummary).mockResolvedValue(mockSummary);

    render(<SimpleQCReview projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Blocking Issues \(1\)/)).toBeInTheDocument();
    });

    const approveBtn = screen.getByTestId('approve-production-btn');
    expect(approveBtn).toBeDisabled();

    // Attempting to click disabled approval button does nothing
    fireEvent.click(approveBtn);
    expect(apiClient.approveProduction).not.toHaveBeenCalled();
  });
});
