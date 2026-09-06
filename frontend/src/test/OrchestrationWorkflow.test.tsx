import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AutomationBar } from '../components/storyboard/AutomationBar';
import { QCHistoryPanel } from '../components/qc/QCHistoryPanel';
import type { OrchestrationStateResponse, OrchestrationAuditResponse, Project } from '../api/types';

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
});
