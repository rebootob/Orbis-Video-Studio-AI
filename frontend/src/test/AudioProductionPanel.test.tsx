import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AudioProductionPanel } from '../components/audio/AudioProductionPanel';
import { api } from '../api/client';
import type { AudioClip, AudioPlan } from '../api/types';

vi.mock('../api/client', () => ({
  api: {
    getAudioPlan: vi.fn(),
    generateAudioPlan: vi.fn(),
    approveAudioPlan: vi.fn(),
    listAudioClips: vi.fn(),
    generateClipAudio: vi.fn(),
    updateAudioClip: vi.fn(),
    executeAudioBatch: vi.fn(),
    computeAudioMix: vi.fn(),
  },
}));

describe('AudioProductionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders audio panel and loads tracks and plan summary', async () => {
    const mockPlan: AudioPlan = {
      id: 'plan-1',
      project_id: 'proj-1',
      status: 'DRAFT',
      version: 1,
      plan_data: {
        auto_mix: {
          default_ducking_amount_db: -12.0,
          speech_intervals: [{ start: 0, end: 4, duck_attenuation_db: -12 }],
        },
      },
    };

    const mockClips: AudioClip[] = [
      {
        id: 'clip-1',
        project_id: 'proj-1',
        name: 'Shot 1 - VO',
        audio_type: 'VO',
        source_type: 'GENERATED_AUDIO',
        generation_mode: 'SEPARATE_AUDIO',
        scope: 'SHOT',
        prompt: 'Welcome to Orbis Video Studio',
        start_time: 0.0,
        duration_seconds: 4.0,
        volume: 1.0,
        mute: false,
        fade_in: 0.0,
        fade_out: 0.0,
        ducking_role: 'FOREGROUND',
        ducking_amount_db: 0.0,
        is_locked: false,
        status: 'PENDING',
        version: 1,
      },
      {
        id: 'clip-2',
        project_id: 'proj-1',
        name: 'Main Theme BGM',
        audio_type: 'BGM',
        source_type: 'GENERATED_AUDIO',
        generation_mode: 'SEPARATE_AUDIO',
        scope: 'PROJECT',
        prompt: 'Cinematic orchestral background score',
        start_time: 0.0,
        duration_seconds: 30.0,
        volume: 0.8,
        mute: false,
        fade_in: 1.0,
        fade_out: 1.0,
        ducking_role: 'BACKGROUND',
        ducking_amount_db: -12.0,
        is_locked: false,
        status: 'READY',
        version: 1,
      },
    ];

    vi.mocked(api.getAudioPlan).mockResolvedValue(mockPlan);
    vi.mocked(api.listAudioClips).mockResolvedValue(mockClips);

    render(<AudioProductionPanel projectId="proj-1" projectStatus="VIDEO_APPROVED" />);

    expect(screen.getByTestId('audio-production-panel')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Audio Plan Status:')).toBeInTheDocument();
      expect(screen.getByText('Shot 1 - VO')).toBeInTheDocument();
      expect(screen.getByText('Main Theme BGM')).toBeInTheDocument();
    });

    // Check 3D orthogonal badges
    expect(screen.getAllByText('GENERATED_AUDIO').length).toBeGreaterThan(0);
    expect(screen.getAllByText('SEPARATE_AUDIO').length).toBeGreaterThan(0);
    expect(screen.getByText('SHOT')).toBeInTheDocument();
    expect(screen.getByText('PROJECT')).toBeInTheDocument();
  });

  it('handles generating audio plan on button click', async () => {
    vi.mocked(api.getAudioPlan).mockRejectedValue(new Error('Not found'));
    vi.mocked(api.listAudioClips).mockResolvedValue([]);

    const newPlan: AudioPlan = {
      id: 'plan-2',
      project_id: 'proj-1',
      status: 'DRAFT',
      version: 1,
    };
    vi.mocked(api.generateAudioPlan).mockResolvedValue(newPlan);

    render(<AudioProductionPanel projectId="proj-1" />);

    const generateBtn = screen.getByTestId('generate-audio-plan-btn');
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(api.generateAudioPlan).toHaveBeenCalledWith('proj-1');
    });
  });
});
