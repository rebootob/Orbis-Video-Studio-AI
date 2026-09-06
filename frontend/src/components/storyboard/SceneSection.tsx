import React, { useState } from 'react';
import type { Scene, Shot, GenerationJob } from '../../api/types';
import { ShotCard } from './ShotCard';
import {
  Plus,
  Edit2,
  Archive,
  Check,
  Lock,
  Unlock,
  Clapperboard,
  Copy,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';

interface SceneSectionProps {
  scene: Scene;
  shots: Shot[];
  jobsByShotId: Record<string, GenerationJob>;
  selectedShotId: string | null;
  selectedShotIds?: Set<string>;
  canMoveSceneUp?: boolean;
  canMoveSceneDown?: boolean;
  onSelectShot: (shot: Shot) => void;
  onToggleSelectShot?: (shotId: string) => void;
  onAddShot: (sceneId: string) => void;
  onUpdateScene: (sceneId: string, payload: Partial<Scene>) => void;
  onDeleteScene: (sceneId: string) => void;
  onDuplicateScene?: (sceneId: string) => void;
  onMoveSceneUp?: (sceneId: string) => void;
  onMoveSceneDown?: (sceneId: string) => void;
  onMoveShotUp?: (sceneId: string, shotId: string) => void;
  onMoveShotDown?: (sceneId: string, shotId: string) => void;
  onToggleShotLock: (shot: Shot) => void;
  onToggleSceneLock: (scene: Scene) => void;
}

export const SceneSection: React.FC<SceneSectionProps> = ({
  scene,
  shots,
  jobsByShotId,
  selectedShotId,
  selectedShotIds,
  canMoveSceneUp = false,
  canMoveSceneDown = false,
  onSelectShot,
  onToggleSelectShot,
  onAddShot,
  onUpdateScene,
  onDeleteScene,
  onDuplicateScene,
  onMoveSceneUp,
  onMoveSceneDown,
  onMoveShotUp,
  onMoveShotDown,
  onToggleShotLock,
  onToggleSceneLock,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [heading, setHeading] = useState(scene.heading || `Scene ${scene.scene_number}`);
  const [setting, setSetting] = useState(scene.setting || '');

  const handleSaveScene = () => {
    onUpdateScene(scene.id, { heading, setting });
    setIsEditing(false);
  };

  // Sort shots by shot_number
  const sortedShots = [...shots].sort((a, b) => a.shot_number - b.shot_number);

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        padding: '16px',
        marginBottom: '24px',
      }}
      data-testid={`scene-section-${scene.id}`}
    >
      {/* Scene Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          paddingBottom: '14px',
          borderBottom: '1px solid var(--border-subtle)',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
          <Clapperboard size={18} color="#818cf8" />
          {isEditing ? (
            <div style={{ display: 'flex', gap: '8px', flex: 1, maxWidth: '480px' }}>
              <input
                type="text"
                value={heading}
                onChange={(e) => setHeading(e.target.value)}
                placeholder="Scene Heading (e.g. INT. COMMAND CENTER - NIGHT)"
                style={{ flex: 2 }}
              />
              <input
                type="text"
                value={setting}
                onChange={(e) => setSetting(e.target.value)}
                placeholder="Setting notes"
                style={{ flex: 1 }}
              />
              <button className="btn btn-sm btn-primary" onClick={handleSaveScene}>
                <Check size={14} />
              </button>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h4 style={{ fontSize: '1rem', fontWeight: '600' }}>
                  Scene #{scene.scene_number}: {scene.heading || 'Untitled Scene'}
                </h4>
                {scene.is_locked && (
                  <span className="badge badge-locked" style={{ fontSize: '0.65rem' }}>
                    <Lock size={10} /> Locked
                  </span>
                )}
              </div>
              {scene.setting && (
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Setting: {scene.setting}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Scene Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* Reorder Scene buttons */}
          {canMoveSceneUp && onMoveSceneUp && (
            <button
              className="btn btn-xs btn-outline"
              onClick={() => onMoveSceneUp(scene.id)}
              title="Move Scene Up"
            >
              <ChevronUp size={12} />
            </button>
          )}
          {canMoveSceneDown && onMoveSceneDown && (
            <button
              className="btn btn-xs btn-outline"
              onClick={() => onMoveSceneDown(scene.id)}
              title="Move Scene Down"
            >
              <ChevronDown size={12} />
            </button>
          )}

          {/* Duplicate Scene */}
          {onDuplicateScene && (
            <button
              className="btn btn-xs btn-secondary"
              onClick={() => onDuplicateScene(scene.id)}
              title="Duplicate Scene (and shots)"
              data-testid={`duplicate-scene-${scene.id}`}
            >
              <Copy size={12} /> Duplicate
            </button>
          )}

          {/* Lock/Unlock */}
          <button
            className="btn btn-xs btn-outline"
            onClick={() => onToggleSceneLock(scene)}
            title={scene.is_locked ? 'Unlock Scene' : 'Lock Scene'}
          >
            {scene.is_locked ? <Unlock size={12} /> : <Lock size={12} />}
            {scene.is_locked ? 'Unlock' : 'Lock'}
          </button>

          {!isEditing && (
            <button
              className="btn btn-xs btn-secondary"
              onClick={() => setIsEditing(true)}
              disabled={scene.is_locked}
              title="Rename Scene"
            >
              <Edit2 size={12} /> Edit
            </button>
          )}

          <button
            className="btn btn-xs btn-outline"
            onClick={() => {
              if (confirm(`Archive Scene #${scene.scene_number}? All scene and shot records will be safely retained in history.`)) {
                onDeleteScene(scene.id);
              }
            }}
            disabled={scene.is_locked}
            title="Archive Scene (Retains history)"
            data-testid={`archive-scene-${scene.id}`}
          >
            <Archive size={12} /> Archive
          </button>

          <button
            className="btn btn-sm btn-primary"
            onClick={() => onAddShot(scene.id)}
            disabled={scene.is_locked}
            data-testid={`add-shot-btn-${scene.id}`}
          >
            <Plus size={14} /> Add Shot
          </button>
        </div>
      </div>

      {/* Shots Grid */}
      {sortedShots.length === 0 ? (
        <div
          style={{
            padding: '24px',
            textAlign: 'center',
            backgroundColor: 'var(--bg-app)',
            borderRadius: '8px',
            border: '1px dashed var(--border-default)',
            color: 'var(--text-muted)',
            fontSize: '0.8125rem',
          }}
        >
          No shots planned for this scene yet. Click "+ Add Shot" or use "Create Full Storyboard" above.
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '16px',
          }}
        >
          {sortedShots.map((shot, idx) => (
            <ShotCard
              key={shot.id}
              shot={shot}
              latestJob={jobsByShotId[shot.id]}
              isSelected={selectedShotId === shot.id}
              isMultiSelected={selectedShotIds ? selectedShotIds.has(shot.id) : false}
              canMoveUp={idx > 0}
              canMoveDown={idx < sortedShots.length - 1}
              onSelect={() => onSelectShot(shot)}
              onToggleSelect={
                onToggleSelectShot
                  ? (e) => {
                      e.stopPropagation();
                      onToggleSelectShot(shot.id);
                    }
                  : undefined
              }
              onMoveUp={
                onMoveShotUp
                  ? (e) => {
                      e.stopPropagation();
                      onMoveShotUp(scene.id, shot.id);
                    }
                  : undefined
              }
              onMoveDown={
                onMoveShotDown
                  ? (e) => {
                      e.stopPropagation();
                      onMoveShotDown(scene.id, shot.id);
                    }
                  : undefined
              }
              onToggleLock={(e) => {
                e.stopPropagation();
                onToggleShotLock(shot);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};
