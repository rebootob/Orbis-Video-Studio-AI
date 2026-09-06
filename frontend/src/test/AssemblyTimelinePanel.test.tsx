import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { SimpleTimelinePanel } from '../components/assembly/SimpleTimelinePanel';
import { api } from '../api/client';
import type { AssemblyTimeline } from '../api/types';

vi.mock('../api/client', () => ({
  api: {
    getAssemblyTimeline: vi.fn(),
    autoAssembleTimeline: vi.fn(),
    updateShotPlacement: vi.fn(),
    reorderScenes: vi.fn(),
    reorderShotsInScene: vi.fn(),
    moveShotToScene: vi.fn(),
    createTimelineCheckpoint: vi.fn(),
    listTimelineCheckpoints: vi.fn(),
    restoreTimelineCheckpoint: vi.fn(),
    getTimelineBlockers: vi.fn(),
    applyTimelineFix: vi.fn(),
  },
}));

describe('SimpleTimelinePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders assembly timeline and loads scenes and player', async () => {
    const mockTimeline: AssemblyTimeline = {
      id: 'timeline-1',
      project_id: 'proj-1',
      version: 1,
      status: 'DRAFT',
      is_active: true,
      total_duration: 9.5,
      scene_count: 1,
      shot_count: 2,
      scenes: [
        {
          id: 'ascene-1',
          timeline_id: 'timeline-1',
          scene_id: 'scene-1',
          scene_order: 0,
          scene_title: 'Scene #1',
          placements: [
            {
              id: 'pl-1',
              timeline_id: 'timeline-1',
              assembly_scene_id: 'ascene-1',
              scene_id: 'scene-1',
              shot_id: 'shot-1',
              shot_order: 0,
              visual_asset_id: 'asset-1',
              source_type: 'VIDEO',
              trim_in: 0.0,
              trim_out: 5.5,
              effective_duration: 5.5,
              still_duration: 4.0,
              transition_to_next: 'CUT',
              is_locked: false,
              version: 1,
              shot_title: 'Shot 1 Title',
              created_at: '2026-09-07T00:00:00Z',
              updated_at: '2026-09-07T00:00:00Z',
            },
            {
              id: 'pl-2',
              timeline_id: 'timeline-1',
              assembly_scene_id: 'ascene-1',
              scene_id: 'scene-1',
              shot_id: 'shot-2',
              shot_order: 1,
              visual_asset_id: 'asset-2',
              source_type: 'KEYFRAME',
              trim_in: 0.0,
              trim_out: 4.0,
              effective_duration: 4.0,
              still_duration: 4.0,
              transition_to_next: 'FADE',
              is_locked: false,
              version: 1,
              shot_title: 'Shot 2 Keyframe',
              created_at: '2026-09-07T00:00:00Z',
              updated_at: '2026-09-07T00:00:00Z',
            },
          ],
        },
      ],
      audio_clips: [
        {
          id: 'aclip-1',
          audio_type: 'VO',
          scope: 'SHOT',
          name: 'VO Track 1',
          start_time: 0.0,
          duration_seconds: 4.0,
          volume: 1.0,
          is_muted: false,
        },
      ],
      blockers: [],
      created_at: '2026-09-07T00:00:00Z',
      updated_at: '2026-09-07T00:00:00Z',
    };

    vi.mocked(api.getAssemblyTimeline).mockResolvedValue(mockTimeline);
    vi.mocked(api.listTimelineCheckpoints).mockResolvedValue([]);

    render(<SimpleTimelinePanel projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Simplified Assembly & Preview/i)).toBeInTheDocument();
    });

    expect(screen.getByText('Shot 1 Title')).toBeInTheDocument();
    expect(screen.getByText('Shot 2 Keyframe')).toBeInTheDocument();
  });

  it('triggers auto assembly on button click', async () => {
    const mockTimeline: AssemblyTimeline = {
      id: 'timeline-1',
      project_id: 'proj-1',
      version: 1,
      status: 'DRAFT',
      is_active: true,
      total_duration: 0.0,
      scene_count: 0,
      shot_count: 0,
      scenes: [],
      audio_clips: [],
      blockers: [],
      created_at: '2026-09-07T00:00:00Z',
      updated_at: '2026-09-07T00:00:00Z',
    };

    vi.mocked(api.getAssemblyTimeline).mockResolvedValue(mockTimeline);
    vi.mocked(api.listTimelineCheckpoints).mockResolvedValue([]);
    vi.mocked(api.autoAssembleTimeline).mockResolvedValue(mockTimeline);

    render(<SimpleTimelinePanel projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Simplified Assembly & Preview/i)).toBeInTheDocument();
    });

    const assembleBtn = screen.getAllByRole('button', { name: /Auto Assemble/i })[0];
    fireEvent.click(assembleBtn);

    await waitFor(() => {
      expect(api.autoAssembleTimeline).toHaveBeenCalledWith('proj-1');
    });
  });
});
