import React, { useState } from 'react';
import type { Scene, Shot, GenerationJob } from '../../api/types';
import { AutomationBar } from './AutomationBar';
import { SceneSection } from './SceneSection';
import { ShotDetailDrawer } from './ShotDetailDrawer';
import { Plus } from 'lucide-react';

interface StoryboardGridProps {
  scenes: Scene[];
  shots: Shot[];
  jobs: GenerationJob[];
  automationStep: string | null;
  onGenerateFullStoryboard: () => Promise<void>;
  onBatchGenerateShots: () => Promise<void>;
  onRetryFailed: () => Promise<void>;
  onAddScene: () => Promise<void>;
  onUpdateScene: (sceneId: string, payload: Partial<Scene>) => Promise<void>;
  onDeleteScene: (sceneId: string) => Promise<void>;
  onAddShot: (sceneId: string) => Promise<void>;
  onUpdateShot: (shotId: string, payload: Partial<Shot>) => Promise<void>;
  onDeleteShot: (shotId: string) => Promise<void>;
  onToggleShotLock: (shot: Shot) => Promise<void>;
  onToggleSceneLock: (scene: Scene) => Promise<void>;
  onGenerateShot: (shotId: string) => Promise<void>;
}

export const StoryboardGrid: React.FC<StoryboardGridProps> = ({
  scenes,
  shots,
  jobs,
  automationStep,
  onGenerateFullStoryboard,
  onBatchGenerateShots,
  onRetryFailed,
  onAddScene,
  onUpdateScene,
  onDeleteScene,
  onAddShot,
  onUpdateShot,
  onDeleteShot,
  onToggleShotLock,
  onToggleSceneLock,
  onGenerateShot,
}) => {
  const [selectedShotId, setSelectedShotId] = useState<string | null>(null);

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

  return (
    <div data-testid="storyboard-grid">
      {/* High-Level Automation Bar */}
      <AutomationBar
        automationStep={automationStep}
        onGenerateFullStoryboard={onGenerateFullStoryboard}
        onBatchGenerateShots={onBatchGenerateShots}
        onRetryFailed={onRetryFailed}
        hasFailedJobs={hasFailedJobs}
        totalShots={shots.length}
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
            Use high-level automation to generate a full storyboard from your project brief,
            or add your first scene manually below.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
            <button
              className="btn btn-primary"
              onClick={onGenerateFullStoryboard}
              data-testid="empty-state-generate-btn"
            >
              Create Full Storyboard (Auto)
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
          {scenes.map((scene) => (
            <SceneSection
              key={scene.id}
              scene={scene}
              shots={shotsBySceneId[scene.id] || []}
              jobsByShotId={latestJobByShotId}
              selectedShotId={selectedShotId}
              onSelectShot={(s) => setSelectedShotId(s.id)}
              onAddShot={onAddShot}
              onUpdateScene={onUpdateScene}
              onDeleteScene={onDeleteScene}
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
          onClose={() => setSelectedShotId(null)}
          onUpdateShot={onUpdateShot}
          onDeleteShot={onDeleteShot}
          onToggleLock={onToggleShotLock}
          onGenerateShot={onGenerateShot}
        />
      )}
    </div>
  );
};
