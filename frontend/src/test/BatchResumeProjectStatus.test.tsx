import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../App';
import { api } from '../api/client';
import type { Project, Scene, Shot } from '../api/types';

vi.mock('../api/client', () => ({
  api: {
    listProjects: vi.fn(),
    listProviders: vi.fn(),
    listProjectScenes: vi.fn(),
    listSceneShots: vi.fn(),
    listProjectStories: vi.fn(),
    getProjectStory: vi.fn(),
    listProjectJobs: vi.fn(),
    listProjectReferences: vi.fn(),
    getProjectBudget: vi.fn(),
    listProjectLedger: vi.fn(),
    resumeProjectJobs: vi.fn(),
    updateProject: vi.fn(),
    estimateBatchJobs: vi.fn(),
    listBatchRuns: vi.fn(),
  },
}));

const mockProject: Project = {
  id: 'proj-batch-1',
  title: 'Batch Safety Project',
  description: 'Testing batch safety',
  status: 'SHOT_PLAN_APPROVED',
  video_mode: 'STORY',
  purpose: 'Marketing',
  target_platform: 'YouTube',
  target_duration_seconds: 60,
  preferred_aspect_ratio: '16:9',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockScene: Scene = {
  id: 'scene-1',
  project_id: 'proj-batch-1',
  scene_number: 1,
  heading: 'EXT. SPACE STATION - NIGHT',
  duration_seconds: 5.0,
  is_locked: false,
};

const mockShot: Shot = {
  id: 'shot-1',
  scene_id: 'scene-1',
  shot_number: 1,
  shot_type: 'AI_GENERATED',
  duration_seconds: 4.0,
  visual_prompt: 'Spaceship dock',
  is_locked: false,
  status: 'PENDING',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('Batch Generation Status Advancement Safety', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.alert = vi.fn();
    window.confirm = vi.fn(() => true);

    (api.listProjects as any).mockResolvedValue([mockProject]);
    (api.listProviders as any).mockResolvedValue([]);
    (api.listProjectScenes as any).mockResolvedValue([mockScene]);
    (api.listSceneShots as any).mockResolvedValue([mockShot]);
    (api.getProjectStory as any).mockResolvedValue(null);
    (api.listProjectJobs as any).mockResolvedValue([]);
    (api.listProjectReferences as any).mockResolvedValue([]);
    (api.getProjectBudget as any).mockResolvedValue({
      project_id: 'proj-batch-1',
      budget_limit: 100,
      currency: 'USD',
      confirmed_cost: 0,
      estimated_cost: 0,
      total_committed_cost: 0,
      soft_limit_exceeded: false,
      hard_limit_exceeded: false,
      has_unknown_costs: false,
    });
    (api.listProjectLedger as any).mockResolvedValue([]);
    (api.estimateBatchJobs as any).mockResolvedValue({
      shot_count: 1,
      skipped_count: 0,
      total_evaluated: 1,
      estimated_cost_total: 0.1,
      currency: 'USD',
      has_unknown_pricing: false,
      warning_messages: [],
    });
    (api.listBatchRuns as any).mockResolvedValue([]);
  });

  it('does NOT transition Project status to VIDEO_IN_PROGRESS when queued_count is 0', async () => {
    (api.resumeProjectJobs as any).mockResolvedValue({
      id: 'run-1',
      project_id: 'proj-batch-1',
      operation_type: 'CONTINUE_INCOMPLETE',
      status: 'DISPATCHED',
      requested_count: 1,
      eligible_count: 0,
      queued_count: 0,
      skipped_count: 1,
      completed_count: 0,
      failed_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<App />);

    const projectCard = await screen.findByText('Batch Safety Project');
    fireEvent.click(projectCard);

    await screen.findByText('Spaceship dock');

    const batchBtn = await screen.findByTestId('batch-generate-shots-btn');
    fireEvent.click(batchBtn);

    const confirmBtn = await screen.findByTestId('confirm-dispatch-btn', {}, { timeout: 4000 });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.resumeProjectJobs).toHaveBeenCalledTimes(1);
    });

    expect(api.updateProject).not.toHaveBeenCalledWith(
      'proj-batch-1',
      expect.objectContaining({ status: 'VIDEO_IN_PROGRESS' })
    );
  });

  it('transitions Project status to VIDEO_IN_PROGRESS when queued_count > 0', async () => {
    (api.resumeProjectJobs as any).mockResolvedValue({
      id: 'run-2',
      project_id: 'proj-batch-1',
      operation_type: 'CONTINUE_INCOMPLETE',
      status: 'DISPATCHED',
      requested_count: 1,
      eligible_count: 1,
      queued_count: 1,
      skipped_count: 0,
      completed_count: 0,
      failed_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<App />);

    const projectCard = await screen.findByText('Batch Safety Project');
    fireEvent.click(projectCard);

    await screen.findByText('Spaceship dock');

    const batchBtn = await screen.findByTestId('batch-generate-shots-btn');
    fireEvent.click(batchBtn);

    const confirmBtn = await screen.findByTestId('confirm-dispatch-btn', {}, { timeout: 4000 });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.resumeProjectJobs).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(api.listProjects).toHaveBeenCalled();
    });

    expect(api.updateProject).not.toHaveBeenCalledWith(
      'proj-batch-1',
      expect.objectContaining({ status: 'VIDEO_IN_PROGRESS' })
    );
  });

  it('does NOT transition Project status to VIDEO_IN_PROGRESS when handleRetryFailed queues 0 jobs', async () => {
    (api.listProjectJobs as any).mockResolvedValue([
      {
        id: 'job-failed-1',
        shot_id: 'shot-1',
        provider_name: 'vidu',
        status: 'FAILED',
        error_message: 'Provider timed out',
        created_at: new Date().toISOString(),
      },
    ]);
    (api.resumeProjectJobs as any).mockResolvedValue({
      id: 'run-retry-0',
      project_id: 'proj-batch-1',
      operation_type: 'RETRY_FAILED',
      status: 'NO_OP',
      requested_count: 1,
      eligible_count: 0,
      queued_count: 0,
      skipped_count: 1,
      completed_count: 0,
      failed_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<App />);

    const projectCard = await screen.findByText('Batch Safety Project');
    fireEvent.click(projectCard);

    const retryBtn = await screen.findByTestId('retry-failed-jobs-btn');
    fireEvent.click(retryBtn);

    const confirmBtn = await screen.findByTestId('confirm-dispatch-btn', {}, { timeout: 4000 });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.resumeProjectJobs).toHaveBeenCalledWith('proj-batch-1', {
        operation_type: 'RETRY_FAILED',
      });
    });

    expect(api.updateProject).not.toHaveBeenCalledWith(
      'proj-batch-1',
      expect.objectContaining({ status: 'VIDEO_IN_PROGRESS' })
    );
  });

  it('transitions Project status to VIDEO_IN_PROGRESS when handleRetryFailed queues > 0 jobs', async () => {
    (api.listProjectJobs as any).mockResolvedValue([
      {
        id: 'job-failed-2',
        shot_id: 'shot-1',
        provider_name: 'vidu',
        status: 'FAILED',
        error_message: 'Provider timed out',
        created_at: new Date().toISOString(),
      },
    ]);
    (api.resumeProjectJobs as any).mockResolvedValue({
      id: 'run-retry-1',
      project_id: 'proj-batch-1',
      operation_type: 'RETRY_FAILED',
      status: 'DISPATCHED',
      requested_count: 1,
      eligible_count: 1,
      queued_count: 1,
      skipped_count: 0,
      completed_count: 0,
      failed_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<App />);

    const projectCard = await screen.findByText('Batch Safety Project');
    fireEvent.click(projectCard);

    const retryBtn = await screen.findByTestId('retry-failed-jobs-btn');
    fireEvent.click(retryBtn);

    const confirmBtn = await screen.findByTestId('confirm-dispatch-btn', {}, { timeout: 4000 });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.resumeProjectJobs).toHaveBeenCalledWith('proj-batch-1', {
        operation_type: 'RETRY_FAILED',
      });
    });

    await waitFor(() => {
      expect(api.listProjects).toHaveBeenCalled();
    });

    expect(api.updateProject).not.toHaveBeenCalledWith(
      'proj-batch-1',
      expect.objectContaining({ status: 'VIDEO_IN_PROGRESS' })
    );
  });
});
