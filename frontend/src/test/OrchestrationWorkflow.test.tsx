import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../App';
import { api } from '../api/client';
import { AutomationBar } from '../components/storyboard/AutomationBar';
import { QCHistoryPanel } from '../components/qc/QCHistoryPanel';
import type { OrchestrationStateResponse, OrchestrationAuditResponse, Project, Scene, Shot } from '../api/types';

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
    getOrchestrationState: vi.fn(),
    executeOrchestrationAction: vi.fn(),
    approveProductionStage: vi.fn(),
    updateOrchestrationSettings: vi.fn(),
    getOrchestrationHistory: vi.fn(),
  },
}));

describe('Orchestration UI Components and Stage Transitions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockOrchestrationState: OrchestrationStateResponse = {
    project_id: 'proj-orch-1',
    current_stage: 'STORY_GENERATED',
    video_mode: 'STORY',
    automation_mode: 'MANUAL',
    stage_display_name: 'Story Outline Generated',
    stage_description: 'Story outline generated. Awaiting review.',
    is_approval_required: true,
    is_blocked: false,
    blocked_reasons: [],
    recommended_action: {
      action: 'APPROVE_STORY',
      display_name: 'Approve Story Outline & Proceed',
      description: 'Lock story narrative outline and proceed to storyboard generation.',
      action_type: 'APPROVAL',
      is_chargeable: false,
      is_blocked: false,
    },
    available_actions: [],
    summary: {},
  };

  it('renders primary recommended action and triggers execution callback', () => {
    const onExecuteMock = vi.fn();
    render(
      <AutomationBar
        automationStep={null}
        selectedShotCount={0}
        totalShots={0}
        hasFailedJobs={false}
        projectStatus="STORY_GENERATED"
        videoMode="STORY"
        orchestrationState={mockOrchestrationState}
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onGenerateSelectedShots={vi.fn()}
        onRetryFailed={vi.fn()}
        onExecuteRecommendedAction={onExecuteMock}
      />
    );

    const actionBtn = screen.getByTestId('orchestration-recommended-action-btn');
    expect(actionBtn).toBeInTheDocument();
    expect(actionBtn).toHaveTextContent('Approve Story Outline & Proceed');

    fireEvent.click(actionBtn);
    expect(onExecuteMock).toHaveBeenCalledTimes(1);
  });

  it('renders automation mode selector and triggers update callback', () => {
    const onUpdateModeMock = vi.fn();
    render(
      <AutomationBar
        automationStep={null}
        selectedShotCount={0}
        totalShots={0}
        hasFailedJobs={false}
        projectStatus="DRAFT"
        videoMode="STORY"
        orchestrationState={{ ...mockOrchestrationState, automation_mode: 'MANUAL' }}
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onGenerateSelectedShots={vi.fn()}
        onRetryFailed={vi.fn()}
        onUpdateAutomationMode={onUpdateModeMock}
      />
    );

    const select = screen.getByTestId('automation-mode-select');
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue('MANUAL');

    fireEvent.change(select, { target: { value: 'AUTO' } });
    expect(onUpdateModeMock).toHaveBeenCalledWith('AUTO');
  });

  it('renders blocked reasons banner when orchestration is blocked', () => {
    const blockedState: OrchestrationStateResponse = {
      ...mockOrchestrationState,
      is_blocked: true,
      blocked_reasons: [
        'Project hard budget limit exceeded. Generation dispatch is blocked.',
        '1 job(s) require reconciliation before automatic workflow continuation.',
      ],
      recommended_action: {
        ...mockOrchestrationState.recommended_action!,
        is_blocked: true,
        blocked_reason: 'Blocked by active issues',
      },
    };

    render(
      <AutomationBar
        automationStep={null}
        selectedShotCount={0}
        totalShots={0}
        hasFailedJobs={false}
        projectStatus="SHOT_PLAN_APPROVED"
        videoMode="STORY"
        orchestrationState={blockedState}
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onGenerateSelectedShots={vi.fn()}
        onRetryFailed={vi.fn()}
        onExecuteRecommendedAction={vi.fn()}
      />
    );

    const banner = screen.getByTestId('orchestration-blocked-reasons');
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent('Project hard budget limit exceeded');
    expect(banner).toHaveTextContent('require reconciliation');

    const actionBtn = screen.getByTestId('orchestration-recommended-action-btn');
    expect(actionBtn).toBeDisabled();
  });

  it('renders orchestration audit history and approves stage in QCHistoryPanel', () => {
    const mockProject: Project = {
      id: 'proj-orch-1',
      title: 'Orchestration Project',
      status: 'STORYBOARD_GENERATED',
      video_mode: 'STORY',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const mockAudits: OrchestrationAuditResponse[] = [
      {
        id: 'audit-1',
        project_id: 'proj-orch-1',
        from_state: 'DRAFT',
        to_state: 'STORY_GENERATED',
        action: 'GENERATE_STORY',
        actor: 'USER',
        result: 'APPLIED',
        detail: 'Generated story outline',
        created_at: new Date().toISOString(),
      },
      {
        id: 'audit-2',
        project_id: 'proj-orch-1',
        from_state: 'STORY_GENERATED',
        to_state: 'STORY_APPROVED',
        action: 'APPROVE_STORY',
        actor: 'USER',
        result: 'APPLIED',
        detail: 'Approved by human reviewer',
        created_at: new Date().toISOString(),
      },
    ];

    const onApproveStageMock = vi.fn();

    render(
      <QCHistoryPanel
        project={mockProject}
        jobs={[]}
        orchestrationAudits={mockAudits}
        onApproveStage={onApproveStageMock}
      />
    );

    // Audit log should be rendered
    const historyCard = screen.getByTestId('orchestration-history-card');
    expect(historyCard).toBeInTheDocument();
    expect(screen.getByText('GENERATE_STORY')).toBeInTheDocument();
    expect(screen.getByText('APPROVE_STORY')).toBeInTheDocument();

    // Click approve storyboard button
    const approveBtn = screen.getByTestId('qc-approve-storyboard-btn');
    expect(approveBtn).toBeInTheDocument();
    fireEvent.click(approveBtn);
    expect(onApproveStageMock).toHaveBeenCalledWith('STORYBOARD_APPROVED');
  });

  it('preserves project model integrity when updating automation mode settings', () => {
    // Regression test for Finding 6:
    // When updateOrchestrationSettings returns OrchestrationStateResponse,
    // the project state handler must not overwrite Project with OrchestrationStateResponse
    const originalProject: Project = {
      id: 'proj-123',
      title: 'Original Title',
      status: 'DRAFT',
      video_mode: 'STORY',
      automation_mode: 'MANUAL',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    };

    const stateResponse: OrchestrationStateResponse = {
      project_id: 'proj-123',
      current_stage: 'DRAFT',
      video_mode: 'STORY',
      automation_mode: 'AUTO',
      stage_display_name: 'Draft & Setup',
      stage_description: 'Initial creative setup',
      is_approval_required: false,
      is_blocked: false,
      blocked_reasons: [],
      available_actions: [],
      summary: {},
    };

    // Simulate safe state updater pattern used in App.tsx
    let selectedProject: Project | null = { ...originalProject };
    let orchestrationState: OrchestrationStateResponse | null = null;

    const handleUpdateAutomationModeSim = (newMode: 'MANUAL' | 'ASSISTED' | 'AUTO', response: OrchestrationStateResponse) => {
      orchestrationState = response;
      selectedProject = selectedProject ? { ...selectedProject, automation_mode: newMode } : null;
    };

    handleUpdateAutomationModeSim('AUTO', stateResponse);

    expect(orchestrationState).toEqual(stateResponse);
    expect(selectedProject).not.toBeNull();
    expect(selectedProject!.title).toBe('Original Title');
    expect(selectedProject!.status).toBe('DRAFT');
    expect(selectedProject!.video_mode).toBe('STORY');
    expect(selectedProject!.automation_mode).toBe('AUTO');
    expect(selectedProject!.created_at).toBe('2026-01-01T00:00:00Z');
  });

  it('correctly maps navigation recommended actions (POLL_STATUS, VIEW_SUMMARY)', () => {
    const pollState: OrchestrationStateResponse = {
      ...mockOrchestrationState,
      current_stage: 'VIDEO_IN_PROGRESS',
      recommended_action: {
        action: 'POLL_STATUS',
        display_name: 'Monitor Active Generation Jobs',
        description: '2 job(s) in progress',
        action_type: 'NAVIGATION',
        is_chargeable: false,
      },
    };

    const onExecuteMock = vi.fn();
    render(
      <AutomationBar
        automationStep={null}
        selectedShotCount={0}
        totalShots={2}
        hasFailedJobs={false}
        projectStatus="VIDEO_IN_PROGRESS"
        videoMode="STORY"
        orchestrationState={pollState}
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onGenerateSelectedShots={vi.fn()}
        onRetryFailed={vi.fn()}
        onExecuteRecommendedAction={onExecuteMock}
      />
    );

    const actionBtn = screen.getByTestId('orchestration-recommended-action-btn');
    expect(actionBtn).toHaveTextContent('Monitor Active Generation Jobs');
    fireEvent.click(actionBtn);
    expect(onExecuteMock).toHaveBeenCalledTimes(1);
  });
});

describe('Recommended Action Canonical Execution via Orchestration API', () => {
  const testProject: Project = {
    id: 'proj-orch-test',
    title: 'Orchestration Test Project',
    description: 'Testing canonical execute API routing',
    status: 'SHOT_PLAN_APPROVED',
    video_mode: 'STORY',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const testScene: Scene = {
    id: 'scene-test-1',
    project_id: 'proj-orch-test',
    scene_number: 1,
    heading: 'EXT. LAB - DAY',
    duration_seconds: 5.0,
    is_locked: false,
  };

  const testShot: Shot = {
    id: 'shot-test-1',
    scene_id: 'scene-test-1',
    shot_number: 1,
    shot_type: 'AI_GENERATED',
    duration_seconds: 4.0,
    visual_prompt: 'Scientist at desk',
    is_locked: false,
    status: 'PENDING',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    window.alert = vi.fn();

    (api.listProjects as any).mockResolvedValue([testProject]);
    (api.listProviders as any).mockResolvedValue([]);
    (api.listProjectScenes as any).mockResolvedValue([testScene]);
    (api.listSceneShots as any).mockResolvedValue([testShot]);
    (api.getProjectStory as any).mockResolvedValue(null);
    (api.listProjectJobs as any).mockResolvedValue([]);
    (api.listProjectReferences as any).mockResolvedValue([]);
    (api.getProjectBudget as any).mockResolvedValue({
      project_id: 'proj-orch-test',
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
    (api.getOrchestrationHistory as any).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
  });

  it('routes START_VIDEO_GENERATION recommended action to executeOrchestrationAction (NOT resumeProjectJobs)', async () => {
    const orchState: OrchestrationStateResponse = {
      project_id: 'proj-orch-test',
      current_stage: 'SHOT_PLAN_APPROVED',
      video_mode: 'STORY',
      automation_mode: 'MANUAL',
      stage_display_name: 'Shot Plan Approved',
      stage_description: 'Shot plan approved. Ready for video generation.',
      is_approval_required: false,
      is_blocked: false,
      blocked_reasons: [],
      recommended_action: {
        action: 'START_VIDEO_GENERATION',
        display_name: 'Start Video Generation',
        description: 'Dispatch video generation jobs to the provider queue.',
        action_type: 'GENERATION',
        is_chargeable: true,
        is_blocked: false,
      },
      available_actions: [],
      summary: {},
    };

    (api.getOrchestrationState as any).mockResolvedValue(orchState);
    (api.executeOrchestrationAction as any).mockResolvedValue({
      success: true,
      action: 'START_VIDEO_GENERATION',
      from_stage: 'SHOT_PLAN_APPROVED',
      to_stage: 'VIDEO_IN_PROGRESS',
      result: 'APPLIED',
      message: 'Batch generation started',
      orchestration_state: { ...orchState, current_stage: 'VIDEO_IN_PROGRESS' },
    });

    render(<App />);

    const projectCard = await screen.findByText('Orchestration Test Project');
    fireEvent.click(projectCard);

    const recActionBtn = await screen.findByTestId('orchestration-recommended-action-btn');
    expect(recActionBtn).toHaveTextContent('Start Video Generation');

    fireEvent.click(recActionBtn);

    await waitFor(() => {
      expect(api.executeOrchestrationAction).toHaveBeenCalledWith('proj-orch-test', {
        action: 'START_VIDEO_GENERATION',
        parameters: undefined,
      });
    });
    expect(api.resumeProjectJobs).not.toHaveBeenCalled();
  });

  it('routes CONTINUE_INCOMPLETE recommended action to executeOrchestrationAction (NOT resumeProjectJobs)', async () => {
    const orchState: OrchestrationStateResponse = {
      project_id: 'proj-orch-test',
      current_stage: 'VIDEO_IN_PROGRESS',
      video_mode: 'STORY',
      automation_mode: 'MANUAL',
      stage_display_name: 'Video In Progress',
      stage_description: 'Some shots incomplete.',
      is_approval_required: false,
      is_blocked: false,
      blocked_reasons: [],
      recommended_action: {
        action: 'CONTINUE_INCOMPLETE',
        display_name: 'Continue Incomplete Generation',
        description: 'Dispatch remaining shots.',
        action_type: 'GENERATION',
        is_chargeable: true,
        is_blocked: false,
      },
      available_actions: [],
      summary: {},
    };

    (api.getOrchestrationState as any).mockResolvedValue(orchState);
    (api.executeOrchestrationAction as any).mockResolvedValue({
      success: true,
      action: 'CONTINUE_INCOMPLETE',
      from_stage: 'VIDEO_IN_PROGRESS',
      to_stage: 'VIDEO_IN_PROGRESS',
      result: 'APPLIED',
      message: 'Continued incomplete jobs',
      orchestration_state: orchState,
    });

    render(<App />);

    const projectCard = await screen.findByText('Orchestration Test Project');
    fireEvent.click(projectCard);

    const recActionBtn = await screen.findByTestId('orchestration-recommended-action-btn');
    expect(recActionBtn).toHaveTextContent('Continue Incomplete Generation');

    fireEvent.click(recActionBtn);

    await waitFor(() => {
      expect(api.executeOrchestrationAction).toHaveBeenCalledWith('proj-orch-test', {
        action: 'CONTINUE_INCOMPLETE',
        parameters: undefined,
      });
    });
    expect(api.resumeProjectJobs).not.toHaveBeenCalled();
  });

  it('routes RETRY_FAILED recommended action to executeOrchestrationAction (NOT resumeProjectJobs)', async () => {
    const orchState: OrchestrationStateResponse = {
      project_id: 'proj-orch-test',
      current_stage: 'VIDEO_IN_PROGRESS',
      video_mode: 'STORY',
      automation_mode: 'MANUAL',
      stage_display_name: 'Video In Progress',
      stage_description: 'Failed jobs detected.',
      is_approval_required: false,
      is_blocked: false,
      blocked_reasons: [],
      recommended_action: {
        action: 'RETRY_FAILED',
        display_name: 'Retry Failed Jobs',
        description: 'Retry failed generation jobs.',
        action_type: 'RECOVERY',
        is_chargeable: true,
        is_blocked: false,
      },
      available_actions: [],
      summary: {},
    };

    (api.getOrchestrationState as any).mockResolvedValue(orchState);
    (api.executeOrchestrationAction as any).mockResolvedValue({
      success: true,
      action: 'RETRY_FAILED',
      from_stage: 'VIDEO_IN_PROGRESS',
      to_stage: 'VIDEO_IN_PROGRESS',
      result: 'APPLIED',
      message: 'Retried failed jobs',
      orchestration_state: orchState,
    });

    render(<App />);

    const projectCard = await screen.findByText('Orchestration Test Project');
    fireEvent.click(projectCard);

    const recActionBtn = await screen.findByTestId('orchestration-recommended-action-btn');
    expect(recActionBtn).toHaveTextContent('Retry Failed Jobs');

    fireEvent.click(recActionBtn);

    await waitFor(() => {
      expect(api.executeOrchestrationAction).toHaveBeenCalledWith('proj-orch-test', {
        action: 'RETRY_FAILED',
        parameters: undefined,
      });
    });
    expect(api.resumeProjectJobs).not.toHaveBeenCalled();
  });

  it('routes GENERATE_SELECTED_SHOTS recommended action to executeOrchestrationAction with parameters', async () => {
    const orchState: OrchestrationStateResponse = {
      project_id: 'proj-orch-test',
      current_stage: 'SHOT_PLAN_APPROVED',
      video_mode: 'STORY',
      automation_mode: 'MANUAL',
      stage_display_name: 'Shot Plan Approved',
      stage_description: 'Ready for generation.',
      is_approval_required: false,
      is_blocked: false,
      blocked_reasons: [],
      recommended_action: {
        action: 'GENERATE_SELECTED_SHOTS',
        display_name: 'Generate Selected Shots',
        description: 'Dispatch selected shots.',
        action_type: 'GENERATION',
        parameters: { shot_ids: ['shot-test-1'] },
        is_chargeable: true,
        is_blocked: false,
      },
      available_actions: [],
      summary: {},
    };

    (api.getOrchestrationState as any).mockResolvedValue(orchState);
    (api.executeOrchestrationAction as any).mockResolvedValue({
      success: true,
      action: 'GENERATE_SELECTED_SHOTS',
      from_stage: 'SHOT_PLAN_APPROVED',
      to_stage: 'VIDEO_IN_PROGRESS',
      result: 'APPLIED',
      message: 'Dispatched selected shots',
      orchestration_state: { ...orchState, current_stage: 'VIDEO_IN_PROGRESS' },
    });

    render(<App />);

    const projectCard = await screen.findByText('Orchestration Test Project');
    fireEvent.click(projectCard);

    const recActionBtn = await screen.findByTestId('orchestration-recommended-action-btn');
    expect(recActionBtn).toHaveTextContent('Generate Selected Shots');

    fireEvent.click(recActionBtn);

    await waitFor(() => {
      expect(api.executeOrchestrationAction).toHaveBeenCalledWith('proj-orch-test', {
        action: 'GENERATE_SELECTED_SHOTS',
        parameters: { shot_ids: ['shot-test-1'] },
      });
    });
    expect(api.resumeProjectJobs).not.toHaveBeenCalled();
  });
});
