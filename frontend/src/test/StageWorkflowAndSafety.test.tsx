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
