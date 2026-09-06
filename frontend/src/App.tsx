import React, { useState, useEffect, useCallback } from 'react';
import type {
  Project,
  ProjectCreatePayload,
  Scene,
  Shot,
  GenerationJob,
  BudgetSummary,
  CostLedgerEntry,
  ReferenceItem,
  ApprovalStatus,
} from './api/types';
import { api } from './api/client';
import { ProjectDashboard } from './components/dashboard/ProjectDashboard';
import { NewProjectModal } from './components/new-project/NewProjectModal';
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
  const [automationStep, setAutomationStep] = useState<string | null>(null);
  const [loadingQueue, setLoadingQueue] = useState(false);

  // Load all projects on mount
  const loadProjects = useCallback(async () => {
    try {
      setLoadingProjects(true);
      const list = await api.listProjects();
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
  const handleCreateProject = async (payload: ProjectCreatePayload) => {
    const created = await api.createProject(payload);
    await loadProjects();
    setSelectedProject(created);
    setActiveTab('storyboard');
  };

  // Project Deletion
  const handleDeleteProject = async (projectId: string) => {
    await api.deleteProject(projectId);
    if (selectedProject?.id === projectId) {
      setSelectedProject(null);
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

  // High-Level Automation: Generate Full Storyboard
  const handleGenerateFullStoryboard = async () => {
    if (!selectedProject) return;
    try {
      setAutomationStep('Creating Story Brief & Act Structure...');
      await new Promise((r) => setTimeout(r, 400));
      setAutomationStep('Planning Scenes & Camera Setups...');
      await api.generateProjectStory(selectedProject.id);
      setAutomationStep('Building Visual Storyboard & Shot Prompts...');
      await loadWorkspaceData(selectedProject);
    } catch (err: any) {
      alert(`Storyboard generation failed: ${err.message}`);
    } finally {
      setAutomationStep(null);
    }
  };

  // Automation: Batch Generate Shots
  const handleBatchGenerateShots = async () => {
    if (!selectedProject) return;
    try {
      setAutomationStep('Dispatching Batch Generation Jobs...');
      await api.batchGenerateProjectShots(selectedProject.id);
      await loadWorkspaceData(selectedProject);
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
    await api.deleteScene(sceneId);
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
    await api.deleteShot(shotId);
    await loadWorkspaceData(selectedProject);
  };

  const handleGenerateShot = async (shotId: string) => {
    if (!selectedProject) return;
    await api.createJob(shotId);
    await loadWorkspaceData(selectedProject);
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
            {/* Mode Banner */}
            <div style={{ marginBottom: '20px' }}>
              <ModeSpecBanner mode={selectedProject.video_mode} />
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
                scenes={scenes}
                shots={shots}
                jobs={jobs}
                automationStep={automationStep}
                onGenerateFullStoryboard={handleGenerateFullStoryboard}
                onBatchGenerateShots={handleBatchGenerateShots}
                onRetryFailed={handleRetryFailed}
                onAddScene={handleAddScene}
                onUpdateScene={handleUpdateScene}
                onDeleteScene={handleDeleteScene}
                onAddShot={handleAddShot}
                onUpdateShot={handleUpdateShot}
                onDeleteShot={handleDeleteShot}
                onToggleShotLock={handleToggleShotLock}
                onToggleSceneLock={handleToggleSceneLock}
                onGenerateShot={handleGenerateShot}
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
            onDeleteProject={handleDeleteProject}
          />
        </main>
      )}

      {/* New Project Modal */}
      <NewProjectModal
        isOpen={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
        onCreate={handleCreateProject}
      />
    </div>
  );
};

export default App;
