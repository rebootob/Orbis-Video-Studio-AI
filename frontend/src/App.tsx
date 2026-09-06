import React, { useState, useEffect, useCallback } from 'react';
import type {
  Project,
  ProjectCreatePayload,
  Scene,
  Shot,
  Story,
  GenerationJob,
  BudgetSummary,
  CostLedgerEntry,
  ReferenceItem,
  ApprovalStatus,
  ReorderItem,
} from './api/types';
import { api } from './api/client';
import { ProjectDashboard } from './components/dashboard/ProjectDashboard';
import { NewProjectModal } from './components/new-project/NewProjectModal';
import { StoryInspectionModal } from './components/workspace/StoryInspectionModal';
import { WorkspaceHeader } from './components/workspace/WorkspaceHeader';
import { ModeSpecBanner } from './components/workspace/ModeSpecBanner';
import { StoryboardGrid } from './components/storyboard/StoryboardGrid';
import { ReferencesPanel } from './components/references/ReferencesPanel';
import { GenerationQueuePanel } from './components/queue/GenerationQueuePanel';
import { BudgetLedgerPanel } from './components/budget/BudgetLedgerPanel';
import { AudioReadinessPanel } from './components/audio/AudioReadinessPanel';
import { QCHistoryPanel } from './components/qc/QCHistoryPanel';
import {
  Film,
  BookOpen,
  Layers,
  DollarSign,
  Volume2,
  CheckCircle,
} from 'lucide-react';
import './App.css';

export const App: React.FC = () => {
  // Navigation & Project selection
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);

  // Active Workspace Tab
  const [activeTab, setActiveTab] = useState<
    'storyboard' | 'references' | 'queue' | 'budget' | 'audio' | 'qc'
  >('storyboard');

  // Workspace Data
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [shots, setShots] = useState<Shot[]>([]);
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [budget, setBudget] = useState<BudgetSummary | null>(null);
  const [ledgerEntries, setLedgerEntries] = useState<CostLedgerEntry[]>([]);
  const [references, setReferences] = useState<ReferenceItem[]>([]);
  const [story, setStory] = useState<Story | null>(null);
  const [isStoryInspectionOpen, setIsStoryInspectionOpen] = useState(false);
  const [automationStep, setAutomationStep] = useState<string | null>(null);
  const [loadingQueue, setLoadingQueue] = useState(false);

  // Load all projects on mount (including archived for dashboard filters)
  const loadProjects = useCallback(async () => {
    try {
      setLoadingProjects(true);
      const list = await api.listProjects(true);
      setProjects(list);
    } catch (err: any) {
      console.error('Failed to load projects', err);
    } finally {
      setLoadingProjects(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Load workspace state for the selected project
  const loadWorkspaceData = useCallback(async (project: Project) => {
    try {
      // 1. Load Scenes
      const scList = await api.listProjectScenes(project.id);
      setScenes(scList);

      // 2. Load Shots for each Scene
      const allShots: Shot[] = [];
      await Promise.all(
        scList.map(async (sc) => {
          const scShots = await api.listSceneShots(sc.id);
          allShots.push(...scShots);
        })
      );
      // Sort shots by scene number and shot number
      allShots.sort((a, b) => a.shot_number - b.shot_number);
      setShots(allShots);

      // 3. Load Jobs
      const jList = await api.listProjectJobs(project.id);
      setJobs(jList);

      // 4. Load Budget & Ledger
      const bSummary = await api.getProjectBudget(project.id);
      setBudget(bSummary);
      const lEntries = await api.listProjectLedger(project.id);
      setLedgerEntries(lEntries);

      // 5. Load References
      const rItems = await api.listProjectReferences(project.id);
      setReferences(rItems);

      // 6. Load Story (if any)
      const storyData = await api.getProjectStory(project.id);
      setStory(storyData);
    } catch (err: any) {
      console.error('Failed to load workspace data', err);
    }
  }, []);

  useEffect(() => {
    if (selectedProject) {
      loadWorkspaceData(selectedProject);
    }
  }, [selectedProject, loadWorkspaceData]);

  // Project Creation
  const handleCreateProject = async (payload: ProjectCreatePayload, file?: File | null) => {
    const created = await api.createProject(payload);
    if (file) {
      try {
        await api.uploadAsset(created.id, file, 'DOCUMENT', file.name);
      } catch (uploadErr: any) {
        alert(
          `Project "${created.title}" was created, but uploading reference document "${file.name}" failed: ${uploadErr.message || 'Upload error'}. You can re-upload it from the Continuity Bibles tab.`
        );
      }
    }
    await loadProjects();
    setSelectedProject(created);
    setActiveTab('storyboard');
  };

  // Soft-Archive Project
  const handleArchiveProject = async (projectId: string) => {
    await api.archiveProject(projectId);
    if (selectedProject?.id === projectId) {
      setSelectedProject(null);
    }
    await loadProjects();
  };

  // Unarchive Project
  const handleUnarchiveProject = async (projectId: string) => {
    await api.unarchiveProject(projectId);
    await loadProjects();
  };

  // Duplicate Project
  const handleDuplicateProject = async (projectId: string) => {
    const duplicated = await api.duplicateProject(projectId);
    await loadProjects();
    setSelectedProject(duplicated);
    setActiveTab('storyboard');
  };

  // Rename Project
  const handleRenameProject = async (projectId: string, newTitle: string) => {
    await api.updateProject(projectId, { title: newTitle });
    if (selectedProject?.id === projectId) {
      setSelectedProject({ ...selectedProject, title: newTitle });
    }
    await loadProjects();
  };

  // Status / QC Update
  const handleUpdateStatus = async (status: ApprovalStatus) => {
    if (!selectedProject) return;
    const updated = await api.updateProject(selectedProject.id, { status });
    setSelectedProject(updated);
    await loadProjects();
  };

  // Stage Generator: Story (STORY mode only)
  const handleGenerateStory = async () => {
    if (!selectedProject) return;
    try {
      setAutomationStep('Generating Story Brief & Narrative Outline...');
      const storyRes = await api.generateProjectStory(selectedProject.id, { generate_scenes: false });
      setStory(storyRes);
      await api.updateProject(selectedProject.id, { status: 'STORY_GENERATED' });
      await loadWorkspaceData(selectedProject);
      setSelectedProject({ ...selectedProject, status: 'STORY_GENERATED' });
      await loadProjects();
      setIsStoryInspectionOpen(true);
    } catch (err: any) {
      alert(`Story generation failed: ${err.message}`);
    } finally {
      setAutomationStep(null);
    }
  };

  const handleApproveStory = async () => {
    if (!selectedProject) return;
    await handleUpdateStatus('STORY_APPROVED');
    setIsStoryInspectionOpen(false);
  };

  // Stage Generator: Storyboard (Scenes & Shot Structure)
  const handleGenerateStoryboard = async () => {
    if (!selectedProject) return;
    if (selectedProject.video_mode === 'STORY' && selectedProject.status !== 'STORY_APPROVED') {
      alert("Story outline must be approved before generating storyboard scenes. Current stage is '" + selectedProject.status + "'.");
      return;
    }
    try {
      setAutomationStep('Generating Storyboard Scenes & Layout...');
      if (selectedProject.video_mode === 'STORY') {
        if (!story) {
          const s = await api.generateProjectStory(selectedProject.id, { generate_scenes: false });
          setStory(s);
          await api.updateProject(selectedProject.id, { status: 'STORY_GENERATED' });
          await loadWorkspaceData(selectedProject);
          setSelectedProject({ ...selectedProject, status: 'STORY_GENERATED' });
          await loadProjects();
          setIsStoryInspectionOpen(true);
          return;
        }
        await api.generateStoryScenes(story.id, { generate_shots: false });
      } else {
        await api.generateProjectStoryboard(selectedProject.id, { generate_shots: false });
      }
      await api.updateProject(selectedProject.id, { status: 'STORYBOARD_GENERATED' });
      await loadWorkspaceData(selectedProject);
      setSelectedProject({ ...selectedProject, status: 'STORYBOARD_GENERATED' });
      await loadProjects();
    } catch (err: any) {
      alert(`Storyboard generation failed: ${err.message}`);
    } finally {
      setAutomationStep(null);
    }
  };

  // Stage Generator: Detailed Shot Plan & Prompts via Backend Service
  const handleGenerateShotPlan = async () => {
    if (!selectedProject) return;
    if (selectedProject.status !== 'STORYBOARD_APPROVED') {
      alert("Storyboard must be approved before generating shot plans. Current stage is '" + selectedProject.status + "'.");
      return;
    }
    try {
      setAutomationStep('Formulating Detailed Shot Plan & Prompts...');
      if (scenes.length === 0) {
        throw new Error('Please generate storyboard scenes before generating shot plans.');
      }
      for (const scene of scenes) {
        await api.generateSceneShots(scene.id);
      }
      await api.updateProject(selectedProject.id, { status: 'SHOT_PLAN_GENERATED' });
      await loadWorkspaceData(selectedProject);
      setSelectedProject({ ...selectedProject, status: 'SHOT_PLAN_GENERATED' });
      await loadProjects();
    } catch (err: any) {
      alert(`Shot plan generation failed: ${err.message}`);
    } finally {
      setAutomationStep(null);
    }
  };

  // High-Level Automation: Generate Storyboard according to mode
  const handleGenerateFullStoryboard = async () => {
    if (!selectedProject) return;
    if (selectedProject.video_mode === 'STORY' && (!story || selectedProject.status === 'DRAFT')) {
      await handleGenerateStory();
    } else {
      await handleGenerateStoryboard();
    }
  };

  // Automation: Batch Generate Shots (Selected or All Incomplete)
  const handleBatchGenerateShots = async (shotIds?: string[] | null, onlyIncomplete = true) => {
    if (!selectedProject) return;
    const allowedStatuses = [
      'SHOT_PLAN_APPROVED',
      'IMAGES_GENERATED',
      'VIDEO_IN_PROGRESS',
      'FINAL_REVIEW',
      'READY_FOR_REVIEW',
      'COMPLETED',
      'APPROVED',
    ];
    if (!allowedStatuses.includes(selectedProject.status)) {
      alert("Shot Plan must be approved before batch generating video. Current stage is '" + selectedProject.status + "'.");
      return;
    }
    try {
      setAutomationStep('Dispatching Batch Generation Jobs...');
      await api.batchGenerateProjectShots(selectedProject.id, {
        shot_ids: shotIds || undefined,
        only_incomplete: onlyIncomplete,
      });
      await api.updateProject(selectedProject.id, { status: 'VIDEO_IN_PROGRESS' });
      await loadWorkspaceData(selectedProject);
      setSelectedProject({ ...selectedProject, status: 'VIDEO_IN_PROGRESS' });
      await loadProjects();
    } catch (err: any) {
      alert(`Batch generation failed: ${err.message}`);
    } finally {
      setAutomationStep(null);
    }
  };

  // Retry Failed Jobs
  const handleRetryFailed = async () => {
    if (!selectedProject) return;
    const failed = jobs.filter((j) => j.status === 'FAILED');
    for (const j of failed) {
      try {
        await api.createJob(j.shot_id, j.provider_name);
      } catch (err: any) {
        console.error('Retry error', err);
      }
    }
    await loadWorkspaceData(selectedProject);
  };

  // Scene Operations
  const handleAddScene = async () => {
    if (!selectedProject) return;
    const nextNumber = scenes.length + 1;
    await api.createScene(selectedProject.id, {
      scene_number: nextNumber,
      heading: `EXT. SCENE ${nextNumber} - DAY`,
      setting: 'Location Setting',
      duration_seconds: 5.0,
    });
    await loadWorkspaceData(selectedProject);
  };

  const handleUpdateScene = async (sceneId: string, payload: Partial<Scene>) => {
    if (!selectedProject) return;
    await api.updateScene(sceneId, payload);
    await loadWorkspaceData(selectedProject);
  };

  const handleDeleteScene = async (sceneId: string) => {
    if (!selectedProject) return;
    try {
      await api.deleteScene(sceneId);
      await loadWorkspaceData(selectedProject);
    } catch (err: any) {
      alert(`Cannot delete scene: ${err.message}`);
    }
  };

  const handleDuplicateScene = async (sceneId: string) => {
    if (!selectedProject) return;
    await api.duplicateScene(sceneId);
    await loadWorkspaceData(selectedProject);
  };

  const handleReorderScenes = async (items: ReorderItem[]) => {
    if (!selectedProject) return;
    await api.reorderScenes(selectedProject.id, items);
    await loadWorkspaceData(selectedProject);
  };

  // Shot Operations
  const handleAddShot = async (sceneId: string) => {
    if (!selectedProject) return;
    const sceneShots = shots.filter((s) => s.scene_id === sceneId);
    const nextShotNum = sceneShots.length + 1;
    await api.createShot(sceneId, {
      shot_number: nextShotNum,
      shot_type: 'AI_GENERATED',
      visual_prompt: 'Cinematic shot establishing key subject in atmospheric environment',
      duration_seconds: 4.0,
    });
    await loadWorkspaceData(selectedProject);
  };

  const handleUpdateShot = async (shotId: string, payload: Partial<Shot>) => {
    if (!selectedProject) return;
    await api.updateShot(shotId, payload);
    await loadWorkspaceData(selectedProject);
  };

  const handleDeleteShot = async (shotId: string) => {
    if (!selectedProject) return;
    try {
      await api.deleteShot(shotId);
      await loadWorkspaceData(selectedProject);
    } catch (err: any) {
      alert(`Cannot delete shot: ${err.message}`);
    }
  };

  const handleReorderShots = async (sceneId: string, items: ReorderItem[]) => {
    if (!selectedProject) return;
    await api.reorderShots(sceneId, items);
    await loadWorkspaceData(selectedProject);
  };

  const handleGenerateShot = async (shotId: string) => {
    if (!selectedProject) return;
    const allowedStatuses = [
      'SHOT_PLAN_APPROVED',
      'IMAGES_GENERATED',
      'VIDEO_IN_PROGRESS',
      'FINAL_REVIEW',
      'READY_FOR_REVIEW',
      'COMPLETED',
      'APPROVED',
    ];
    if (!allowedStatuses.includes(selectedProject.status)) {
      alert("Shot Plan must be approved before production generation. Current stage is '" + selectedProject.status + "'.");
      return;
    }
    try {
      await api.createJob(shotId);
      await loadWorkspaceData(selectedProject);
    } catch (err: any) {
      alert(`Shot generation dispatch failed: ${err.message}`);
    }
  };

  // Lock Toggles
  const handleToggleShotLock = async (shot: Shot) => {
    if (!selectedProject) return;
    try {
      if (shot.is_locked) {
        await api.unlockEntity(selectedProject.id, 'SHOT', shot.id);
      } else {
        await api.lockEntity(selectedProject.id, 'SHOT', shot.id);
      }
      await loadWorkspaceData(selectedProject);
    } catch (err: any) {
      alert(`Lock action failed: ${err.message}`);
    }
  };

  const handleToggleSceneLock = async (scene: Scene) => {
    if (!selectedProject) return;
    try {
      if (scene.is_locked) {
        await api.unlockEntity(selectedProject.id, 'SCENE', scene.id);
      } else {
        await api.lockEntity(selectedProject.id, 'SCENE', scene.id);
      }
      await loadWorkspaceData(selectedProject);
    } catch (err: any) {
      alert(`Lock action failed: ${err.message}`);
    }
  };

  const handleToggleReferenceLock = async (item: ReferenceItem) => {
    if (!selectedProject) return;
    try {
      if (item.is_locked) {
        await api.unlockEntity(selectedProject.id, item.reference_type, item.id);
      } else {
        await api.lockEntity(selectedProject.id, item.reference_type, item.id);
      }
      await loadWorkspaceData(selectedProject);
    } catch (err: any) {
      alert(`Lock action failed: ${err.message}`);
    }
  };

  // Queue Operations
  const handleRefreshJobs = async () => {
    if (!selectedProject) return;
    try {
      setLoadingQueue(true);
      const jList = await api.listProjectJobs(selectedProject.id);
      setJobs(jList);
    } finally {
      setLoadingQueue(false);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    if (!selectedProject) return;
    await api.cancelJob(jobId);
    await loadWorkspaceData(selectedProject);
  };

  const handlePollJob = async (jobId: string) => {
    if (!selectedProject) return;
    await api.pollJob(jobId);
    await loadWorkspaceData(selectedProject);
  };

  // Budget Update
  const handleUpdateBudget = async (limit: number | null, threshold: number) => {
    if (!selectedProject) return;
    await api.updateProjectBudget(selectedProject.id, limit, 'USD', threshold);
    await loadWorkspaceData(selectedProject);
  };

  // Next Best Action dispatcher
  const handleNextBestAction = (action: string) => {
    switch (action) {
      case 'GENERATE_STORY':
        handleGenerateStory();
        break;
      case 'APPROVE_STORY':
        setIsStoryInspectionOpen(true);
        break;
      case 'GENERATE_STORYBOARD':
        handleGenerateStoryboard();
        break;
      case 'APPROVE_STORYBOARD':
        handleUpdateStatus('STORYBOARD_APPROVED');
        break;
      case 'GENERATE_SHOT_PLAN':
        handleGenerateShotPlan();
        break;
      case 'APPROVE_SHOT_PLAN':
        handleUpdateStatus('SHOT_PLAN_APPROVED');
        break;
      case 'BATCH_GENERATE':
        setActiveTab('storyboard');
        break;
      case 'MONITOR_QUEUE':
        setActiveTab('queue');
        break;
      case 'APPROVE_PROJECT':
        handleUpdateStatus('COMPLETED');
        break;
      case 'VIEW_QC':
        setActiveTab('qc');
        break;
      default:
        break;
    }
  };

  const completedShotsCount = jobs.filter((j) => j.status === 'COMPLETED').length;

  return (
    <div className="app-container">
      {selectedProject ? (
        <>
          {/* Workspace Shell */}
          <WorkspaceHeader
            project={selectedProject}
            budget={budget}
            jobs={jobs}
            onBackToDashboard={() => setSelectedProject(null)}
            onUpdateStatus={handleUpdateStatus}
          />

          <main className="main-content">
            {/* Mode & Next Best Action Guidance Banner */}
            <div style={{ marginBottom: '20px' }}>
              <ModeSpecBanner
                mode={selectedProject.video_mode}
                status={selectedProject.status}
                shotCount={shots.length}
                completedShotCount={completedShotsCount}
                onAction={handleNextBestAction}
              />
            </div>

            {/* Tab Navigation */}
            <nav className="tab-bar" aria-label="Workspace Sections">
              <button
                className={`tab-item ${activeTab === 'storyboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('storyboard')}
                data-testid="tab-storyboard"
              >
                <Film size={16} /> Storyboard & Shots ({shots.length})
              </button>
              <button
                className={`tab-item ${activeTab === 'references' ? 'active' : ''}`}
                onClick={() => setActiveTab('references')}
                data-testid="tab-references"
              >
                <BookOpen size={16} /> Continuity Bibles ({references.length})
              </button>
              <button
                className={`tab-item ${activeTab === 'queue' ? 'active' : ''}`}
                onClick={() => setActiveTab('queue')}
                data-testid="tab-queue"
              >
                <Layers size={16} /> Generation Queue ({jobs.length})
              </button>
              <button
                className={`tab-item ${activeTab === 'budget' ? 'active' : ''}`}
                onClick={() => setActiveTab('budget')}
                data-testid="tab-budget"
              >
                <DollarSign size={16} /> Budget & Ledger
              </button>
              <button
                className={`tab-item ${activeTab === 'audio' ? 'active' : ''}`}
                onClick={() => setActiveTab('audio')}
                data-testid="tab-audio"
              >
                <Volume2 size={16} /> Audio Readiness
              </button>
              <button
                className={`tab-item ${activeTab === 'qc' ? 'active' : ''}`}
                onClick={() => setActiveTab('qc')}
                data-testid="tab-qc"
              >
                <CheckCircle size={16} /> Quality & History
              </button>
            </nav>

            {/* Tab Panels */}
            {activeTab === 'storyboard' && (
              <StoryboardGrid
                projectId={selectedProject.id}
                scenes={scenes}
                shots={shots}
                jobs={jobs}
                automationStep={automationStep}
                projectStatus={selectedProject.status}
                videoMode={selectedProject.video_mode}
                onGenerateFullStoryboard={handleGenerateFullStoryboard}
                onBatchGenerateShots={handleBatchGenerateShots}
                onRetryFailed={handleRetryFailed}
                onAddScene={handleAddScene}
                onUpdateScene={handleUpdateScene}
                onDeleteScene={handleDeleteScene}
                onDuplicateScene={handleDuplicateScene}
                onReorderScenes={handleReorderScenes}
                onAddShot={handleAddShot}
                onUpdateShot={handleUpdateShot}
                onDeleteShot={handleDeleteShot}
                onReorderShots={handleReorderShots}
                onToggleShotLock={handleToggleShotLock}
                onToggleSceneLock={handleToggleSceneLock}
                onGenerateShot={handleGenerateShot}
                onStageReview={(st) => {
                  if (st === 'STORY') {
                    setIsStoryInspectionOpen(true);
                  } else if (st === 'STORYBOARD') {
                    setActiveTab('storyboard');
                  } else if (st === 'SHOT_PLAN') {
                    setActiveTab('storyboard');
                  }
                }}
              />
            )}

            {activeTab === 'references' && (
              <ReferencesPanel
                references={references}
                projectId={selectedProject.id}
                onAddCharacter={(d) => api.createCharacter(selectedProject.id, d).then(() => loadWorkspaceData(selectedProject))}
                onAddLocation={(d) => api.createLocation(selectedProject.id, d).then(() => loadWorkspaceData(selectedProject))}
                onAddStyle={(d) => api.createStyle(selectedProject.id, d).then(() => loadWorkspaceData(selectedProject))}
                onAddBrand={(d) => api.createBrand(selectedProject.id, d).then(() => loadWorkspaceData(selectedProject))}
                onToggleLock={handleToggleReferenceLock}
              />
            )}

            {activeTab === 'queue' && (
              <GenerationQueuePanel
                jobs={jobs}
                loading={loadingQueue}
                projectStatus={selectedProject.status}
                onRefreshJobs={handleRefreshJobs}
                onCancelJob={handleCancelJob}
                onPollJob={handlePollJob}
                onRetryJob={handleGenerateShot}
              />
            )}

            {activeTab === 'budget' && (
              <BudgetLedgerPanel
                budget={budget}
                ledgerEntries={ledgerEntries}
                onUpdateBudget={handleUpdateBudget}
              />
            )}

            {activeTab === 'audio' && (
              <AudioReadinessPanel projectId={selectedProject.id} />
            )}

            {activeTab === 'qc' && (
              <QCHistoryPanel
                project={selectedProject}
                jobs={jobs}
                budget={budget}
                onUpdateStatus={handleUpdateStatus}
              />
            )}
          </main>
        </>
      ) : (
        /* Dashboard View */
        <main className="main-content">
          <ProjectDashboard
            projects={projects}
            loading={loadingProjects}
            onSelectProject={(p) => {
              setSelectedProject(p);
              setActiveTab('storyboard');
            }}
            onOpenNewProjectModal={() => setIsNewProjectOpen(true)}
            onDeleteProject={handleArchiveProject}
            onArchiveProject={handleArchiveProject}
            onUnarchiveProject={handleUnarchiveProject}
            onDuplicateProject={handleDuplicateProject}
            onRenameProject={handleRenameProject}
          />
        </main>
      )}

      {/* New Project Modal */}
      <NewProjectModal
        isOpen={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
        onCreate={handleCreateProject}
      />

      {/* Story Inspection Modal */}
      {selectedProject && (
        <StoryInspectionModal
          isOpen={isStoryInspectionOpen}
          story={story}
          projectTitle={selectedProject.title}
          projectStatus={selectedProject.status}
          onClose={() => setIsStoryInspectionOpen(false)}
          onApprove={handleApproveStory}
          onRegenerate={handleGenerateStory}
        />
      )}
    </div>
  );
};

export default App;
