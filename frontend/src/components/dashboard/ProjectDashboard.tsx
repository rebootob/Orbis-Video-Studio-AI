import React, { useState } from 'react';
import type { Project, VideoMode } from '../../api/types';
import { Plus, Search, Film, Sparkles, Clock, Trash2, ArrowRight } from 'lucide-react';

interface ProjectDashboardProps {
  projects: Project[];
  loading: boolean;
  onSelectProject: (project: Project) => void;
  onOpenNewProjectModal: () => void;
  onDeleteProject: (projectId: string) => void;
}

export const ProjectDashboard: React.FC<ProjectDashboardProps> = ({
  projects,
  loading,
  onSelectProject,
  onOpenNewProjectModal,
  onDeleteProject,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedMode, setSelectedMode] = useState<string>('ALL');

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.purpose && p.purpose.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesMode = selectedMode === 'ALL' || p.video_mode === selectedMode;
    return matchesSearch && matchesMode;
  });

  const getModeBadgeClass = (mode: VideoMode) => {
    switch (mode) {
      case 'STORY':
        return 'badge-story';
      case 'SHORT':
        return 'badge-short';
      case 'LOOP':
        return 'badge-loop';
      case 'SCENE':
        return 'badge-scene';
      default:
        return 'badge-draft';
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'APPROVED':
        return 'badge-approved';
      case 'LOCKED':
        return 'badge-locked';
      case 'READY_FOR_REVIEW':
        return 'badge-review';
      case 'NEEDS_ATTENTION':
        return 'badge-attention';
      default:
        return 'badge-draft';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner / Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: 'var(--text-primary)' }}>
            Studio Projects
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '4px' }}>
            Manage and produce multi-mode generative video projects
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={onOpenNewProjectModal}
          data-testid="create-project-btn"
        >
          <Plus size={16} /> New Project
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px',
          flexWrap: 'wrap',
          backgroundColor: 'var(--bg-panel)',
          padding: '12px 16px',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ position: 'relative', minWidth: '280px', flex: 1 }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }}
          />
          <input
            type="text"
            placeholder="Search projects by title, purpose, description..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: '100%', paddingLeft: '36px' }}
            data-testid="project-search-input"
          />
        </div>

        {/* Mode Chips */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto' }}>
          {['ALL', 'STORY', 'SHORT', 'LOOP', 'SCENE'].map((mode) => (
            <button
              key={mode}
              className={`btn btn-sm ${selectedMode === mode ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedMode(mode)}
              data-testid={`mode-filter-${mode.toLowerCase()}`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div
          style={{
            textAlign: 'center',
            padding: '60px 0',
            color: 'var(--text-secondary)',
          }}
        >
          Loading studio projects...
        </div>
      ) : filteredProjects.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '64px 20px',
            backgroundColor: 'var(--bg-panel)',
            borderRadius: '12px',
            border: '1px dashed var(--border-default)',
          }}
        >
          <Film size={48} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
          <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>No projects found</h3>
          <p
            style={{
              color: 'var(--text-secondary)',
              fontSize: '0.875rem',
              maxWidth: '400px',
              margin: '0 auto 20px auto',
            }}
          >
            {searchTerm || selectedMode !== 'ALL'
              ? 'No projects match your filter criteria. Try clearing filters or searching for something else.'
              : 'Create your first mode-aware video project to start planning storyboards and shots.'}
          </p>
          <button className="btn btn-primary" onClick={onOpenNewProjectModal}>
            <Plus size={16} /> Create Project
          </button>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '20px',
          }}
        >
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              className="card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '16px',
                cursor: 'pointer',
              }}
              onClick={() => onSelectProject(project)}
              data-testid={`project-card-${project.id}`}
            >
              <div>
                {/* Header with Badges */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '10px',
                  }}
                >
                  <span className={`badge ${getModeBadgeClass(project.video_mode)}`}>
                    {project.video_mode}
                  </span>
                  <span className={`badge ${getStatusBadgeClass(project.status)}`}>
                    {project.status}
                  </span>
                </div>

                {/* Title and Purpose */}
                <h3
                  style={{
                    fontSize: '1.125rem',
                    fontWeight: '600',
                    color: 'var(--text-primary)',
                    marginBottom: '6px',
                  }}
                >
                  {project.title}
                </h3>
                {project.purpose && (
                  <p
                    style={{
                      fontSize: '0.8125rem',
                      color: 'var(--text-secondary)',
                      lineHeight: '1.4',
                      marginBottom: '10px',
                    }}
                  >
                    {project.purpose}
                  </p>
                )}
                {project.description && (
                  <p
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)',
                      lineHeight: '1.4',
                    }}
                  >
                    {project.description.length > 90
                      ? `${project.description.slice(0, 90)}...`
                      : project.description}
                  </p>
                )}
              </div>

              {/* Specs & Budget Footer */}
              <div>
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '8px',
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)',
                    marginBottom: '14px',
                    paddingTop: '10px',
                    borderTop: '1px solid var(--border-subtle)',
                  }}
                >
                  {project.preferred_aspect_ratio && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <Sparkles size={12} /> {project.preferred_aspect_ratio}
                    </span>
                  )}
                  {project.target_duration_seconds && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} /> {project.target_duration_seconds}s
                    </span>
                  )}
                  {project.target_platform && (
                    <span>• {project.target_platform}</span>
                  )}
                  {project.budget_limit != null && (
                    <span>• Cap: ${project.budget_limit} {project.budget_currency || 'USD'}</span>
                  )}
                </div>

                {/* Actions */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <button
                    className="btn btn-xs btn-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete project "${project.title}"? This cannot be undone.`)) {
                        onDeleteProject(project.id);
                      }
                    }}
                    title="Delete Project"
                  >
                    <Trash2 size={12} />
                  </button>

                  <button
                    className="btn btn-sm btn-primary"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectProject(project);
                    }}
                  >
                    Open Workspace <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
