import React, { useState } from 'react';
import type { Scene, Shot, GenerationJob, ReorderItem } from '../../api/types';
import { AutomationBar } from './AutomationBar';
import { SceneSection } from './SceneSection';
import { ShotDetailDrawer } from './ShotDetailDrawer';
import { CostConfirmationModal } from '../workspace/CostConfirmationModal';
import { Plus } from 'lucide-react';

interface StoryboardGridProps {
  projectId: string;
  scenes: Scene[];
  shots: Shot[];
  jobs: GenerationJob[];
  automationStep: string | null;
  projectStatus?: string;
  videoMode?: string;
  onGenerateFullStoryboard: () => Promise<void>;
  onBatchGenerateShots: (shotIds?: string[] | null, onlyIncomplete?: boolean) => Promise<void>;
  onRetryFailed: () => Promise<void>;
  onAddScene: () => Promise<void>;
  onUpdateScene: (sceneId: string, payload: Partial<Scene>) => Promise<void>;
  onDeleteScene: (sceneId: string) => Promise<void>;
  onDuplicateScene?: (sceneId: string) => Promise<void>;
  onReorderScenes?: (items: ReorderItem[]) => Promise<void>;
  onAddShot: (sceneId: string) => Promise<void>;
  onUpdateShot: (shotId: string, payload: Partial<Shot>) => Promise<void>;
  onDeleteShot: (shotId: string) => Promise<void>;
  onReorderShots?: (sceneId: string, items: ReorderItem[]) => Promise<void>;
  onToggleShotLock: (shot: Shot) => Promise<void>;
  onToggleSceneLock: (scene: Scene) => Promise<void>;
  onGenerateShot: (shotId: string) => Promise<void>;
  onStageReview?: (stage: 'STORY' | 'STORYBOARD' | 'SHOT_PLAN') => void;
}

export const StoryboardGrid: React.FC<StoryboardGridProps> = ({
  projectId,
  scenes,
  shots,
  jobs,
  automationStep,
  projectStatus,
  videoMode,
  onGenerateFullStoryboard,
  onBatchGenerateShots,
  onRetryFailed,
  onAddScene,
  onUpdateScene,
  onDeleteScene,
  onDuplicateScene,
  onReorderScenes,
  onAddShot,
  onUpdateShot,
  onDeleteShot,
  onReorderShots,
  onToggleShotLock,
  onToggleSceneLock,
  onGenerateShot,
  onStageReview,
}) => {
  const [selectedShotId, setSelectedShotId] = useState<string | null>(null);
  const [selectedShotIds, setSelectedShotIds] = useState<Set<string>>(new Set());

  // Cost confirmation modal state
  const [costModalOpen, setCostModalOpen] = useState(false);
  const [costModalShotIds, setCostModalShotIds] = useState<string[] | null>(null);
  const [costModalOnlyIncomplete, setCostModalOnlyIncomplete] = useState(true);

  // Group shots by scene
  const shotsBySceneId: Record<string, Shot[]> = {};
  scenes.forEach((s) => {
    shotsBySceneId[s.id] = [];
  });
  shots.forEach((shot) => {
    if (shotsBySceneId[shot.scene_id]) {
      shotsBySceneId[shot.scene_id].push(shot);
    } else {
      shotsBySceneId[shot.scene_id] = [shot];
    }
  });

  // Map latest job per shot
  const latestJobByShotId: Record<string, GenerationJob> = {};
  jobs.forEach((job) => {
    if (!latestJobByShotId[job.shot_id]) {
      latestJobByShotId[job.shot_id] = job;
    }
  });

  const selectedShot = shots.find((s) => s.id === selectedShotId) || null;
  const hasFailedJobs = jobs.some((j) => j.status === 'FAILED');

  // Toggle selection of shot
  const handleToggleSelectShot = (shotId: string) => {
    setSelectedShotIds((prev) => {
      const next = new Set(prev);
      if (next.has(shotId)) {
        next.delete(shotId);
      } else {
        next.add(shotId);
      }
      return next;
    });
  };

  // Scene reordering
  const handleMoveSceneUp = (sceneId: string) => {
    const idx = scenes.findIndex((s) => s.id === sceneId);
    if (idx <= 0 || !onReorderScenes) return;
    const items: ReorderItem[] = [
      { id: scenes[idx].id, order: scenes[idx - 1].scene_number },
      { id: scenes[idx - 1].id, order: scenes[idx].scene_number },
    ];
    onReorderScenes(items);
  };

  const handleMoveSceneDown = (sceneId: string) => {
    const idx = scenes.findIndex((s) => s.id === sceneId);
    if (idx < 0 || idx >= scenes.length - 1 || !onReorderScenes) return;
    const items: ReorderItem[] = [
      { id: scenes[idx].id, order: scenes[idx + 1].scene_number },
      { id: scenes[idx + 1].id, order: scenes[idx].scene_number },
    ];
    onReorderScenes(items);
  };

  // Shot reordering
  const handleMoveShotUp = (sceneId: string, shotId: string) => {
    const sceneShots = [...(shotsBySceneId[sceneId] || [])].sort(
      (a, b) => a.shot_number - b.shot_number
    );
    const idx = sceneShots.findIndex((s) => s.id === shotId);
    if (idx <= 0 || !onReorderShots) return;
    const items: ReorderItem[] = [
      { id: sceneShots[idx].id, order: sceneShots[idx - 1].shot_number },
      { id: sceneShots[idx - 1].id, order: sceneShots[idx].shot_number },
    ];
    onReorderShots(sceneId, items);
  };

  const handleMoveShotDown = (sceneId: string, shotId: string) => {
    const sceneShots = [...(shotsBySceneId[sceneId] || [])].sort(
      (a, b) => a.shot_number - b.shot_number
    );
    const idx = sceneShots.findIndex((s) => s.id === shotId);
    if (idx < 0 || idx >= sceneShots.length - 1 || !onReorderShots) return;
    const items: ReorderItem[] = [
      { id: sceneShots[idx].id, order: sceneShots[idx + 1].shot_number },
      { id: sceneShots[idx + 1].id, order: sceneShots[idx].shot_number },
    ];
    onReorderShots(sceneId, items);
  };

  // Batch trigger helpers
  const triggerBatchIncomplete = () => {
    setCostModalShotIds(null);
    setCostModalOnlyIncomplete(true);
    setCostModalOpen(true);
  };

  const triggerSelectedShots = () => {
    if (selectedShotIds.size === 0) return;
    setCostModalShotIds(Array.from(selectedShotIds));
    setCostModalOnlyIncomplete(false);
    setCostModalOpen(true);
  };

  return (
    <div data-testid="storyboard-grid">
      {/* High-Level Automation Bar */}
      <AutomationBar
        automationStep={automationStep}
        selectedShotCount={selectedShotIds.size}
        totalShots={shots.length}
        hasFailedJobs={hasFailedJobs}
        projectStatus={projectStatus}
        videoMode={videoMode}
        onGenerateFullStoryboard={onGenerateFullStoryboard}
        onBatchGenerateShots={triggerBatchIncomplete}
        onGenerateSelectedShots={triggerSelectedShots}
        onRetryFailed={onRetryFailed}
        onStageReview={onStageReview}
      />

      {/* Scenes List */}
      {scenes.length === 0 ? (
        <div
          style={{
            backgroundColor: 'var(--bg-panel)',
            borderRadius: '12px',
            padding: '60px 20px',
            textAlign: 'center',
            border: '1px dashed var(--border-default)',
          }}
        >
          <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>
            Storyboard is Empty
          </h3>
          <p
            style={{
              color: 'var(--text-secondary)',
              fontSize: '0.875rem',
              maxWidth: '450px',
              margin: '0 auto 20px auto',
            }}
          >
            {videoMode === 'STORY'
              ? 'Generate a story brief and outline first, then approve it to generate storyboard scenes.'
              : 'Generate storyboard scenes from your project brief, or add your first scene manually below.'}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
            <button
              className="btn btn-primary"
              onClick={onGenerateFullStoryboard}
              data-testid="empty-state-generate-btn"
            >
              {videoMode === 'STORY' ? 'Generate Story Brief' : 'Generate Storyboard Scenes'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={onAddScene}
              data-testid="empty-state-add-scene-btn"
            >
              <Plus size={16} /> Add Scene Manually
            </button>
          </div>
        </div>
      ) : (
        <div>
          {scenes.map((scene, idx) => (
            <SceneSection
              key={scene.id}
              scene={scene}
              shots={shotsBySceneId[scene.id] || []}
              jobsByShotId={latestJobByShotId}
              selectedShotId={selectedShotId}
              selectedShotIds={selectedShotIds}
              canMoveSceneUp={idx > 0}
              canMoveSceneDown={idx < scenes.length - 1}
              onSelectShot={(s) => setSelectedShotId(s.id)}
              onToggleSelectShot={handleToggleSelectShot}
              onAddShot={onAddShot}
              onUpdateScene={onUpdateScene}
              onDeleteScene={onDeleteScene}
              onDuplicateScene={onDuplicateScene}
              onMoveSceneUp={handleMoveSceneUp}
              onMoveSceneDown={handleMoveSceneDown}
              onMoveShotUp={handleMoveShotUp}
              onMoveShotDown={handleMoveShotDown}
              onToggleShotLock={onToggleShotLock}
              onToggleSceneLock={onToggleSceneLock}
            />
          ))}

          {/* Add Scene Footer Button */}
          <div style={{ display: 'flex', justifyContent: 'center', margin: '24px 0' }}>
            <button
              className="btn btn-outline"
              onClick={onAddScene}
              data-testid="add-new-scene-btn"
            >
              <Plus size={16} /> Add New Scene
            </button>
          </div>
        </div>
      )}

      {/* Selected Shot Detail Drawer */}
      {selectedShot && (
        <ShotDetailDrawer
          shot={selectedShot}
          latestJob={latestJobByShotId[selectedShot.id]}
          projectStatus={projectStatus}
          onClose={() => setSelectedShotId(null)}
          onUpdateShot={onUpdateShot}
          onDeleteShot={onDeleteShot}
          onToggleLock={onToggleShotLock}
          onGenerateShot={onGenerateShot}
        />
      )}

      {/* Pre-Generation Cost Confirmation Dialog */}
      <CostConfirmationModal
        isOpen={costModalOpen}
        projectId={projectId}
        shotIds={costModalShotIds}
        onlyIncomplete={costModalOnlyIncomplete}
        onClose={() => setCostModalOpen(false)}
        onConfirm={async () => {
          await onBatchGenerateShots(costModalShotIds, costModalOnlyIncomplete);
          setSelectedShotIds(new Set());
        }}
      />
    </div>
  );
};
