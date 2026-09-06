import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StoryboardGrid } from '../components/storyboard/StoryboardGrid';
import type { Scene, Shot } from '../api/types';

const mockScenes: Scene[] = [
  {
    id: 'sc-1',
    scene_number: 1,
    heading: 'INT. WORKSHOP - NIGHT',
    setting: 'Dark futuristic workshop',
    is_locked: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockShots: Shot[] = [
  {
    id: 'sh-1',
    scene_id: 'sc-1',
    shot_number: 1,
    shot_type: 'AI_GENERATED',
    visual_prompt: 'Close up on glowing laser diode',
    duration_seconds: 3.5,
    is_locked: false,
    status: 'DRAFT',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'sh-2',
    scene_id: 'sc-1',
    shot_number: 2,
    shot_type: 'AI_GENERATED',
    visual_prompt: 'Wide shot of workbench',
    duration_seconds: 4.0,
    is_locked: true,
    status: 'DRAFT',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

describe('StoryboardGrid', () => {
  it('renders scenes and shots with correct lock indicators', () => {
    render(
      <StoryboardGrid
        scenes={mockScenes}
        shots={mockShots}
        jobs={[]}
        automationStep={null}
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onRetryFailed={vi.fn()}
        onAddScene={vi.fn()}
        onUpdateScene={vi.fn()}
        onDeleteScene={vi.fn()}
        onAddShot={vi.fn()}
        onUpdateShot={vi.fn()}
        onDeleteShot={vi.fn()}
        onToggleShotLock={vi.fn()}
        onToggleSceneLock={vi.fn()}
        onGenerateShot={vi.fn()}
      />
    );

    expect(screen.getByText('Scene #1: INT. WORKSHOP - NIGHT')).toBeInTheDocument();
    expect(screen.getByText('Shot #1')).toBeInTheDocument();
    expect(screen.getByText('Shot #2')).toBeInTheDocument();
    expect(screen.getByText('Close up on glowing laser diode')).toBeInTheDocument();
  });

  it('opens shot detail drawer on click and shows lock status', () => {
    render(
      <StoryboardGrid
        scenes={mockScenes}
        shots={mockShots}
        jobs={[]}
        automationStep={null}
        onGenerateFullStoryboard={vi.fn()}
        onBatchGenerateShots={vi.fn()}
        onRetryFailed={vi.fn()}
        onAddScene={vi.fn()}
        onUpdateScene={vi.fn()}
        onDeleteScene={vi.fn()}
        onAddShot={vi.fn()}
        onUpdateShot={vi.fn()}
        onDeleteShot={vi.fn()}
        onToggleShotLock={vi.fn()}
        onToggleSceneLock={vi.fn()}
        onGenerateShot={vi.fn()}
      />
    );

    const shot1Card = screen.getByTestId('shot-card-sh-1');
    fireEvent.click(shot1Card);

    expect(screen.getByTestId('shot-detail-drawer')).toBeInTheDocument();
    expect(screen.getByText('Shot #1 Details')).toBeInTheDocument();
  });

  it('triggers automation action when clicking Create Full Storyboard', () => {
    const handleGenerate = vi.fn();
    render(
      <StoryboardGrid
        scenes={mockScenes}
        shots={mockShots}
        jobs={[]}
        automationStep={null}
        onGenerateFullStoryboard={handleGenerate}
        onBatchGenerateShots={vi.fn()}
        onRetryFailed={vi.fn()}
        onAddScene={vi.fn()}
        onUpdateScene={vi.fn()}
        onDeleteScene={vi.fn()}
        onAddShot={vi.fn()}
        onUpdateShot={vi.fn()}
        onDeleteShot={vi.fn()}
        onToggleShotLock={vi.fn()}
        onToggleSceneLock={vi.fn()}
        onGenerateShot={vi.fn()}
      />
    );

    const generateBtn = screen.getByTestId('generate-full-storyboard-btn');
    fireEvent.click(generateBtn);

    expect(handleGenerate).toHaveBeenCalled();
  });
});
