import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GenerationQueuePanel } from '../components/queue/GenerationQueuePanel';
import type { GenerationJob } from '../api/types';

describe('GenerationQueuePanel', () => {
  it('displays friendly labels for states and provides retry/cancel actions', () => {
    const jobs: GenerationJob[] = [
      {
        id: 'job-101',
        shot_id: 'shot-a',
        provider_name: 'vidu',
        status: 'POLLING',
        retries: 0,
        max_retries: 3,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 'job-102',
        shot_id: 'shot-b',
        provider_name: 'vidu',
        status: 'FAILED',
        error_message: 'Provider timeout',
        retries: 3,
        max_retries: 3,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 'job-103',
        shot_id: 'shot-c',
        provider_name: 'vidu',
        status: 'RECONCILIATION_REQUIRED',
        retries: 1,
        max_retries: 3,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    const handleCancel = vi.fn();
    const handleRetry = vi.fn();

    render(
      <GenerationQueuePanel
        jobs={jobs}
        loading={false}
        onRefreshJobs={vi.fn()}
        onCancelJob={handleCancel}
        onPollJob={vi.fn()}
        onRetryJob={handleRetry}
      />
    );

    expect(screen.getByText('Generating Video (Polling)')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Reconciliation Required')).toBeInTheDocument();
    expect(screen.getByText('Provider timeout')).toBeInTheDocument();

    // Cancel active job
    const cancelBtn = screen.getByText('Cancel');
    fireEvent.click(cancelBtn);
    expect(handleCancel).toHaveBeenCalledWith('job-101');

    // Retry failed job
    const retryBtn = screen.getByText('Retry');
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledWith('shot-b');

    // Reconciliation row does not show normal retry
    expect(screen.getByText('Investigate')).toBeInTheDocument();
  });
});
