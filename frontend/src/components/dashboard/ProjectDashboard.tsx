import React, { useState } from 'react';
import type { Project, VideoMode } from '../../api/types';
import {
  Plus,
  Search,
  Film,
  Sparkles,
  Clock,
  Archive,
  ArchiveRestore,
  Copy,
  Edit2,
  Check,
  X,
  ArrowRight,
  ArrowUpDown,
  Filter,
} from 'lucide-react';

interface ProjectDashboardProps {
  projects: Project[];
  loading: boolean;
  onSelectProject: (project: Project) => void;
  onOpenNewProjectModal: () => void;
  onDeleteProject: (projectId: string) => void; // Soft-archives
  onArchiveProject?: (projectId: string) => void;
  onUnarchiveProject?: (projectId: string) => void;
  onDuplicateProject?: (projectId: string) => void;
  onRenameProject?: (projectId: string, newTitle: string) => void;
}

export const ProjectDashboard: React.FC<ProjectDashboardProps> = ({
  projects,
  loading,
  onSelectProject,
  onOpenNewProjectModal,
  onDeleteProject,
  onArchiveProject,
  onUnarchiveProject,
  onDuplicateProject,
  onRenameProject,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedMode, setSelectedMode] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ACTIVE');
  const [sortBy, setSortBy] = useState<string>('UPDATED_DESC');
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  // Filtering
  const filteredProjects = projects.filter((p) => {
    const isArchived = p.status?.toUpperCase() === 'ARCHIVED';
    if (statusFilter === 'ACTIVE' && isArchived) return false;
    if (statusFilter === 'ARCHIVED' && !isArchived) return false;
    if (statusFilter === 'DRAFT' && p.status?.toUpperCase() !== 'DRAFT') return false;
    if (statusFilter === 'APPROVED' && p.status?.toUpperCase() !== 'APPROVED' && p.status?.toUpperCase() !== 'FINAL_REVIEW') return false;

    const matchesSearch =
      p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.purpose && p.purpose.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesMode = selectedMode === 'ALL' || p.video_mode === selectedMode;
    return matchesSearch && matchesMode;
  });

  // Sorting
  const sortedProjects = [...filteredProjects].sort((a, b) => {
    if (sortBy === 'UPDATED_DESC') {
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    }
    if (sortBy === 'UPDATED_ASC') {
      return new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
    }
    if (sortBy === 'TITLE_ASC') {
      return a.title.localeCompare(b.title);
    }
    if (sortBy === 'TITLE_DESC') {
      return b.title.localeCompare(a.title);
    }
    if (sortBy === 'CREATED_DESC') {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    }
    return 0;
  });

  // Recent Projects (active only, top 3 by updated_at)
  const recentProjects = [...projects]
    .filter((p) => p.status?.toUpperCase() !== 'ARCHIVED')
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 3);

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
      case 'COMPLETED':
        return 'badge-approved';
      case 'LOCKED':
        return 'badge-locked';
      case 'FINAL_REVIEW':
      case 'READY_FOR_REVIEW':
        return 'badge-review';
      case 'ARCHIVED':
        return 'badge-attention';
      default:
        return 'badge-draft';
    }
  };

  const handleStartRename = (project: Project, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingProjectId(project.id);
    setEditingTitle(project.title);
  };

  const handleSaveRename = (projectId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editingTitle.trim() && onRenameProject) {
      onRenameProject(projectId, editingTitle.trim());
    }
    setEditingProjectId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingProjectId(null);
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
            Multi-project workspace with full-history retention, auditability, and mode-aware planning
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

      {/* Recent Projects Highlight */}
      {projects.length >= 4 && !searchTerm && selectedMode === 'ALL' && statusFilter === 'ACTIVE' && recentProjects.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Recently Active Projects
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '12px',
            }}
          >
            {recentProjects.map((rp) => (
              <div
                key={rp.id}
                onClick={() => onSelectProject(rp)}
                style={{
                  backgroundColor: 'var(--bg-panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                    {rp.title}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {rp.video_mode} • Updated {new Date(rp.updated_at).toLocaleDateString()}
                  </div>
                </div>
                <ArrowRight size={14} color="var(--primary)" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap',
          backgroundColor: 'var(--bg-panel)',
          padding: '12px 16px',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ position: 'relative', minWidth: '240px', flex: 1 }}>
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

        {/* Status Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Filter size={14} color="var(--text-muted)" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ fontSize: '0.8125rem', padding: '6px 10px' }}
            data-testid="status-filter-select"
          >
            <option value="ACTIVE">Active Projects</option>
            <option value="ALL">All Projects</option>
            <option value="ARCHIVED">Archived Projects</option>
            <option value="DRAFT">Draft</option>
            <option value="APPROVED">Approved / Review</option>
          </select>
        </div>

        {/* Sort Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ArrowUpDown size={14} color="var(--text-muted)" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            style={{ fontSize: '0.8125rem', padding: '6px 10px' }}
            data-testid="sort-by-select"
          >
            <option value="UPDATED_DESC">Recently Updated</option>
            <option value="UPDATED_ASC">Oldest Updated</option>
            <option value="TITLE_ASC">Title (A-Z)</option>
            <option value="TITLE_DESC">Title (Z-A)</option>
            <option value="CREATED_DESC">Recently Created</option>
          </select>
        </div>

        {/* Mode Chips */}
        <div style={{ display: 'flex', gap: '6px', overflowX: 'auto' }}>
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
      ) : sortedProjects.length === 0 ? (
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
            {searchTerm || selectedMode !== 'ALL' || statusFilter !== 'ACTIVE'
              ? 'No projects match your current filters. Try changing search or filters.'
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
          {sortedProjects.map((project) => {
            const isArchived = project.status?.toUpperCase() === 'ARCHIVED';
            const isEditing = editingProjectId === project.id;

            return (
              <div
                key={project.id}
                className="card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '16px',
                  cursor: 'pointer',
                  opacity: isArchived ? 0.75 : 1,
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

                  {/* Title & Rename */}
                  {isEditing ? (
                    <div
                      style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        style={{ flex: 1, fontSize: '0.9rem', padding: '4px 8px' }}
                        autoFocus
                      />
                      <button
                        className="btn btn-xs btn-primary"
                        onClick={(e) => handleSaveRename(project.id, e)}
                      >
                        <Check size={12} />
                      </button>
                      <button className="btn btn-xs btn-secondary" onClick={handleCancelRename}>
                        <X size={12} />
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                      <h3
                        style={{
                          fontSize: '1.125rem',
                          fontWeight: '600',
                          color: 'var(--text-primary)',
                          margin: 0,
                          flex: 1,
                        }}
                      >
                        {project.title}
                      </h3>
                      {onRenameProject && !isArchived && (
                        <button
                          className="btn btn-xs btn-outline"
                          style={{ padding: '2px 6px' }}
                          onClick={(e) => handleStartRename(project, e)}
                          title="Rename project"
                        >
                          <Edit2 size={11} />
                        </button>
                      )}
                    </div>
                  )}

                  {/* Purpose */}
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

                {/* Specs & Actions Footer */}
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
                    {project.target_platform && <span>• {project.target_platform}</span>}
                    {project.budget_limit != null && (
                      <span>• Cap: ${project.budget_limit} {project.budget_currency || 'USD'}</span>
                    )}
                  </div>

                  {/* Action Toolbar */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {/* Duplicate Project */}
                      {onDuplicateProject && (
                        <button
                          className="btn btn-xs btn-secondary"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDuplicateProject(project.id);
                          }}
                          title="Duplicate Project (Copy scenes and shots)"
                          data-testid={`duplicate-project-${project.id}`}
                        >
                          <Copy size={12} /> Duplicate
                        </button>
                      )}

                      {/* Archive / Unarchive */}
                      {isArchived ? (
                        <button
                          className="btn btn-xs btn-outline"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onUnarchiveProject) {
                              onUnarchiveProject(project.id);
                            }
                          }}
                          title="Restore / Unarchive Project"
                          data-testid={`unarchive-project-${project.id}`}
                        >
                          <ArchiveRestore size={12} /> Restore
                        </button>
                      ) : (
                        <button
                          className="btn btn-xs btn-outline"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm(`Archive project "${project.title}"? All scenes, shots, and ledger records will be preserved.`)) {
                              if (onArchiveProject) {
                                onArchiveProject(project.id);
                              } else {
                                onDeleteProject(project.id);
                              }
                            }
                          }}
                          title="Archive Project (History retained)"
                          data-testid={`archive-project-${project.id}`}
                        >
                          <Archive size={12} /> Archive
                        </button>
                      )}
                    </div>

                    <button
                      className="btn btn-sm btn-primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectProject(project);
                      }}
                    >
                      Workspace <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
