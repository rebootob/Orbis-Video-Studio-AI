import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProjectDashboard } from '../components/dashboard/ProjectDashboard';
import type { Project } from '../api/types';

const mockProjects: Project[] = [
  {
    id: 'proj-1',
    title: 'Cyberpunk Story',
    description: 'Cinematic neon story',
    status: 'DRAFT',
    video_mode: 'STORY',
    purpose: 'Hero commercial',
    target_platform: 'YouTube',
    target_duration_seconds: 60,
    preferred_aspect_ratio: '16:9',
    budget_limit: 100,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'proj-2',
    title: 'Viral Dance Short',
    description: 'Quick vertical hook',
    status: 'APPROVED',
    video_mode: 'SHORT',
    purpose: 'Social viral',
    target_platform: 'TikTok',
    target_duration_seconds: 15,
    preferred_aspect_ratio: '9:16',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

describe('ProjectDashboard', () => {
  it('renders projects and titles correctly', () => {
    render(
      <ProjectDashboard
        projects={mockProjects}
        loading={false}
        onSelectProject={vi.fn()}
        onOpenNewProjectModal={vi.fn()}
        onDeleteProject={vi.fn()}
      />
    );

    expect(screen.getByText('Cyberpunk Story')).toBeInTheDocument();
    expect(screen.getByText('Viral Dance Short')).toBeInTheDocument();
    expect(screen.getAllByText('STORY').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('SHORT').length).toBeGreaterThanOrEqual(1);
  });


  it('filters projects by search term', () => {
    render(
      <ProjectDashboard
        projects={mockProjects}
        loading={false}
        onSelectProject={vi.fn()}
        onOpenNewProjectModal={vi.fn()}
        onDeleteProject={vi.fn()}
      />
    );

    const searchInput = screen.getByTestId('project-search-input');
    fireEvent.change(searchInput, { target: { value: 'Cyberpunk' } });

    expect(screen.getByText('Cyberpunk Story')).toBeInTheDocument();
    expect(screen.queryByText('Viral Dance Short')).not.toBeInTheDocument();
  });

  it('filters projects by mode chips', () => {
    render(
      <ProjectDashboard
        projects={mockProjects}
        loading={false}
        onSelectProject={vi.fn()}
        onOpenNewProjectModal={vi.fn()}
        onDeleteProject={vi.fn()}
      />
    );

    const shortFilter = screen.getByTestId('mode-filter-short');
    fireEvent.click(shortFilter);

    expect(screen.queryByText('Cyberpunk Story')).not.toBeInTheDocument();
    expect(screen.getByText('Viral Dance Short')).toBeInTheDocument();
  });

  it('triggers onSelectProject when clicking Open Workspace', () => {
    const handleSelect = vi.fn();
    render(
      <ProjectDashboard
        projects={mockProjects}
        loading={false}
        onSelectProject={handleSelect}
        onOpenNewProjectModal={vi.fn()}
        onDeleteProject={vi.fn()}
      />
    );

    const card = screen.getByTestId('project-card-proj-1');
    fireEvent.click(card);

    expect(handleSelect).toHaveBeenCalledWith(mockProjects[0]);
  });

  it('renders truthful placeholder, scene and shot counts, and progress summary', () => {
    const projectWithCounts: Project = {
      ...mockProjects[0],
      scene_count: 3,
      shot_count: 8,
      status: 'STORYBOARD_APPROVED',
    };

    render(
      <ProjectDashboard
        projects={[projectWithCounts]}
        loading={false}
        onSelectProject={vi.fn()}
        onOpenNewProjectModal={vi.fn()}
        onDeleteProject={vi.fn()}
      />
    );

    // Placeholder
    expect(screen.getByTestId('project-thumbnail-placeholder-proj-1')).toBeInTheDocument();
    expect(screen.getByText(/No render preview/)).toBeInTheDocument();

    // Counts
    expect(screen.getByTestId('project-counts-proj-1')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Scenes')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('Shots')).toBeInTheDocument();

    // Truthful Stage Progress
    expect(screen.getByTestId('project-progress-proj-1')).toBeInTheDocument();
    expect(screen.getByText('Stage Progress')).toBeInTheDocument();
    expect(screen.getByText('Storyboard Approved')).toBeInTheDocument();
  });
});
