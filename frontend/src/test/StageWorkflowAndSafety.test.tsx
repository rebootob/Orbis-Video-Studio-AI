import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ModeSpecBanner } from '../components/workspace/ModeSpecBanner';
import { ShotDetailDrawer } from '../components/storyboard/ShotDetailDrawer';
import { QCHistoryPanel } from '../components/qc/QCHistoryPanel';
import type { Shot, Project } from '../api/types';

describe('Mode-Aware Staged Workflow & Next Action Guidance', () => {
  it('includes Story stage and recommends Story Brief for STORY mode in DRAFT', () => {
    const handleAction = vi.fn();
    render(
      <ModeSpecBanner
        mode="STORY"
        status="DRAFT"
        shotCount={0}
        completedShotCount={0}
        onAction={handleAction}
      />
    );

    // In STORY mode, Story stage exists in stage flow
    expect(screen.getByText('Story')).toBeInTheDocument();
    // Recommended action is Generate Story Brief
    expect(screen.getByText('Generate Story Brief')).toBeInTheDocument();

    const actionBtn = screen.getByTestId('next-best-action-btn');
    fireEvent.click(actionBtn);
    expect(handleAction).toHaveBeenCalledWith('GENERATE_STORY');
  });

  it('bypasses Story stage and recommends Storyboard & Scenes for SHORT, LOOP, SCENE modes', () => {
    const handleAction = vi.fn();
    render(
      <ModeSpecBanner
        mode="SHORT"
        status="DRAFT"
        shotCount={0}
        completedShotCount={0}
        onAction={handleAction}
      />
    );

    // In SHORT mode, Story stage is NOT in the stage stepper
    expect(screen.queryByText('Story')).not.toBeInTheDocument();
    // Recommended action directly advances to Storyboard & Scenes
    expect(screen.getByText('Create Storyboard & Scenes')).toBeInTheDocument();

    const actionBtn = screen.getByTestId('next-best-action-btn');
    fireEvent.click(actionBtn);
    expect(handleAction).toHaveBeenCalledWith('GENERATE_STORYBOARD');
  });
});

describe('ShotDetailDrawer Unsaved Edits Protection', () => {
  const mockShot: Shot = {
    id: 'shot-1',
    scene_id: 'scene-1',
    shot_number: 1,
    shot_type: 'AI_GENERATED',
    duration_seconds: 4,
    visual_prompt: 'Initial prompt',
    is_locked: false,
    status: 'PENDING',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  it('guards closing drawer when unsaved edits are dirty', () => {
    const handleClose = vi.fn();
    const handleUpdate = vi.fn();

    // Mock confirm dialog
    const confirmSpy = vi.spyOn(window, 'confirm');

    render(
      <ShotDetailDrawer
        shot={mockShot}
        onClose={handleClose}
        onUpdateShot={handleUpdate}
        onDeleteShot={vi.fn()}
        onToggleLock={vi.fn()}
        onGenerateShot={vi.fn()}
      />
    );

    // Dirty the prompt
    const promptInput = screen.getByTestId('shot-prompt-textarea');
    fireEvent.change(promptInput, { target: { value: 'Edited modified prompt' } });

    expect(screen.getByText(/Unsaved changes/i)).toBeInTheDocument();

    // User cancels the confirm dialog
    confirmSpy.mockReturnValueOnce(false);
    const closeBtn = screen.getByTestId('shot-drawer-close-btn');
    fireEvent.click(closeBtn);

    expect(confirmSpy).toHaveBeenCalledWith('You have unsaved changes in this shot. Discard changes and close?');
    expect(handleClose).not.toHaveBeenCalled();

    // User approves the confirm dialog
    confirmSpy.mockReturnValueOnce(true);
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);

    confirmSpy.mockRestore();
  });
});

describe('QCHistoryPanel Truthful Stage Actions', () => {
  const mockProject: Project = {
    id: 'proj-1',
    title: 'Test Project',
    status: 'STORYBOARD_GENERATED',
    video_mode: 'SHORT',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  it('renders truthful stage review action and rejects arbitrary status toggle buttons', () => {
    const handleUpdateStatus = vi.fn();

    render(
      <QCHistoryPanel
        project={mockProject}
        jobs={[]}
        onUpdateStatus={handleUpdateStatus}
      />
    );

    // Current stage is displayed
    expect(screen.getByText('STORYBOARD GENERATED')).toBeInTheDocument();

    // Stage-specific button appears
    const approveBtn = screen.getByTestId('qc-approve-storyboard-btn');
    expect(approveBtn).toBeInTheDocument();
    fireEvent.click(approveBtn);
    expect(handleUpdateStatus).toHaveBeenCalledWith('STORYBOARD_APPROVED');

    // Arbitrary raw statuses like READY_FOR_REVIEW / LOCKED / NEEDS_ATTENTION are NOT present as buttons
    expect(screen.queryByText('READY FOR REVIEW')).not.toBeInTheDocument();
    expect(screen.queryByText('NEEDS ATTENTION')).not.toBeInTheDocument();
  });
});

describe('StoryInspectionModal Inspectable Artifact & Approval', () => {
  const mockStory = {
    id: 'story-123',
    project_id: 'proj-1',
    title: 'The Cyber Chronicles',
    logline: 'A lone courier must deliver data before dawn.',
    synopsis: 'Full detailed narrative synopsis of the cyber world...',
    tone: 'Cyberpunk Noir',
    target_duration: 120,
    language: 'en',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  it('renders story details, allows inspection, approval, and regeneration', async () => {
    const { StoryInspectionModal } = await import('../components/workspace/StoryInspectionModal');
    const handleApprove = vi.fn();
    const handleRegenerate = vi.fn();
    const handleClose = vi.fn();

    render(
      <StoryInspectionModal
        isOpen={true}
        story={mockStory}
        projectTitle="Test Cyber Project"
        onClose={handleClose}
        onApprove={handleApprove}
        onRegenerate={handleRegenerate}
      />
    );

    expect(screen.getByText('Inspect Story Brief & Narrative Outline')).toBeInTheDocument();
    expect(screen.getByText('The Cyber Chronicles')).toBeInTheDocument();
    expect(screen.getByText('A lone courier must deliver data before dawn.')).toBeInTheDocument();
    expect(screen.getByText('Full detailed narrative synopsis of the cyber world...')).toBeInTheDocument();

    const approveBtn = screen.getByTestId('story-approve-btn');
    fireEvent.click(approveBtn);
    expect(handleApprove).toHaveBeenCalledTimes(1);

    const regenBtn = screen.getByTestId('story-regenerate-btn');
    fireEvent.click(regenBtn);
    expect(handleRegenerate).toHaveBeenCalledTimes(1);
  });
});

describe('AutomationBar Reworded Action & Stage Shortcuts', () => {
  it('renders reworded Generate Storyboard Scenes button and inspection shortcuts', async () => {
    const { AutomationBar } = await import('../components/storyboard/AutomationBar');
    const handleGenerate = vi.fn();
    const handleStageReview = vi.fn();

    render(
      <AutomationBar
        automationStep={null}
        totalShots={0}
        selectedShotCount={0}
        hasFailedJobs={false}
        onGenerateFullStoryboard={handleGenerate}
        onBatchGenerateShots={vi.fn()}
        onGenerateSelectedShots={vi.fn()}
        onRetryFailed={vi.fn()}
        onStageReview={handleStageReview}
      />
    );

    const generateBtn = screen.getByTestId('generate-full-storyboard-btn');
    expect(generateBtn).toHaveTextContent('Generate Storyboard Scenes');

    const inspectStoryBtn = screen.getByTestId('review-stage-story-btn');
    fireEvent.click(inspectStoryBtn);
    expect(handleStageReview).toHaveBeenCalledWith('STORY');

    const inspectStoryboardBtn = screen.getByTestId('review-stage-storyboard-btn');
    fireEvent.click(inspectStoryboardBtn);
    expect(handleStageReview).toHaveBeenCalledWith('STORYBOARD');
  });

  it('disables Storyboard generation when STORY is unapproved, and disables Batch generation when SHOT_PLAN is unapproved', async () => {
    const { AutomationBar } = await import('../components/storyboard/AutomationBar');

    // In STORY mode at STORY_GENERATED stage (unapproved story)
    const { rerender } = render(
      <AutomationBar
        automationStep={null}
        totalShots={0}
        selectedShotCount={0}
        hasFailedJobs={false}
        projectStatus="STORY_GENERATED"
        videoMode="STORY"
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onGenerateSelectedShots={vi.fn()}
        onRetryFailed={vi.fn()}
      />
    );

    const generateBtn = screen.getByTestId('generate-full-storyboard-btn');
    expect(generateBtn).toBeDisabled();
    expect(generateBtn).toHaveAttribute('title', expect.stringContaining('Story outline must be approved'));

    // Batch generate button must also be disabled when not SHOT_PLAN_APPROVED
    const batchBtn = screen.getByTestId('batch-generate-shots-btn');
    expect(batchBtn).toBeDisabled();

    // Rerender after Story approval: Storyboard button becomes enabled
    rerender(
      <AutomationBar
        automationStep={null}
        totalShots={0}
        selectedShotCount={0}
        hasFailedJobs={false}
        projectStatus="STORY_APPROVED"
        videoMode="STORY"
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onGenerateSelectedShots={vi.fn()}
        onRetryFailed={vi.fn()}
      />
    );

    expect(screen.getByTestId('generate-full-storyboard-btn')).not.toBeDisabled();
  });
});

describe('Provider-Neutral Single-Shot Routing', () => {
  it('omits provider_name when not explicitly provided to allow backend config resolution', async () => {
    const { api } = await import('../api/client');
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        id: 'job-1',
        shot_id: 'shot-1',
        provider_name: 'vidu',
        status: 'PENDING',
      }),
    } as any);

    await api.createJob('shot-1');

    expect(fetchSpy).toHaveBeenCalled();
    const lastCall = fetchSpy.mock.calls[0];
    const bodyObj = JSON.parse(lastCall[1]?.body as string);
    // provider_name must NOT be present or must be undefined so backend config resolves
    expect(bodyObj.provider_name).toBeUndefined();
    expect(bodyObj.shot_id).toBe('shot-1');

    fetchSpy.mockRestore();
  });
});

describe('ShotDetailDrawer & Retry Controls Production Stage Gates', () => {
  const mockShot: Shot = {
    id: 'shot-100',
    scene_id: 'scene-1',
    shot_number: 1,
    shot_type: 'AI_GENERATED',
    duration_seconds: 4,
    visual_prompt: 'A sleek spaceship landing on a neon platform',
    is_locked: false,
    status: 'PENDING',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  it('disables Generate Shot button before SHOT_PLAN_APPROVED and enables it after', () => {
    const handleGenerate = vi.fn();

    // 1. In unapproved stage (e.g. STORYBOARD_GENERATED or DRAFT)
    const { rerender } = render(
      <ShotDetailDrawer
        shot={mockShot}
        projectStatus="STORYBOARD_GENERATED"
        onClose={vi.fn()}
        onUpdateShot={vi.fn()}
        onDeleteShot={vi.fn()}
        onToggleLock={vi.fn()}
        onGenerateShot={handleGenerate}
      />
    );

    const generateBtn = screen.getByTestId('drawer-generate-shot-btn');
    expect(generateBtn).toBeDisabled();
    expect(generateBtn).toHaveAttribute(
      'title',
      'Shot Plan must be approved before production generation.'
    );
    expect(screen.getByTestId('drawer-production-gated-warning')).toBeInTheDocument();

    // 2. In approved stage (SHOT_PLAN_APPROVED)
    rerender(
      <ShotDetailDrawer
        shot={mockShot}
        projectStatus="SHOT_PLAN_APPROVED"
        onClose={vi.fn()}
        onUpdateShot={vi.fn()}
        onDeleteShot={vi.fn()}
        onToggleLock={vi.fn()}
        onGenerateShot={handleGenerate}
      />
    );

    expect(generateBtn).not.toBeDisabled();
    expect(screen.queryByTestId('drawer-production-gated-warning')).not.toBeInTheDocument();
  });

  it('disables retry controls when production stage is regressed / unapproved', async () => {
    const { AutomationBar } = await import('../components/storyboard/AutomationBar');
    const { GenerationQueuePanel } = await import('../components/queue/GenerationQueuePanel');

    // AutomationBar Retry Failed button is disabled when project is regressed
    render(
      <AutomationBar
        automationStep={null}
        totalShots={2}
        selectedShotCount={0}
        hasFailedJobs={true}
        projectStatus="STORYBOARD_GENERATED"
        videoMode="STORY"
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onGenerateSelectedShots={vi.fn()}
        onRetryFailed={vi.fn()}
      />
    );

    const retryFailedBtn = screen.getByTestId('retry-failed-jobs-btn');
    expect(retryFailedBtn).toBeDisabled();
    expect(retryFailedBtn).toHaveAttribute(
      'title',
      'Shot Plan must be approved before retrying production jobs.'
    );

    // GenerationQueuePanel Retry button is disabled when project is regressed
    const mockJobs = [
      {
        id: 'job-f1',
        shot_id: 'shot-100',
        provider_name: 'vidu',
        status: 'FAILED' as const,
        retries: 1,
        max_retries: 3,
        created_at: new Date().toISOString(),
      },
    ];

    render(
      <GenerationQueuePanel
        jobs={mockJobs}
        loading={false}
        projectStatus="STORYBOARD_GENERATED"
        onRefreshJobs={vi.fn()}
        onCancelJob={vi.fn()}
        onPollJob={vi.fn()}
        onRetryJob={vi.fn()}
      />
    );

    const retryRowBtn = screen.getByText('Retry');
    expect(retryRowBtn.closest('button')).toBeDisabled();
    expect(retryRowBtn.closest('button')).toHaveAttribute(
      'title',
      'Shot Plan must be approved before retrying production jobs.'
    );
  });
});
