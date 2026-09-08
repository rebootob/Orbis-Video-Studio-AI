import React, { useState } from 'react';
import type { Scene, Shot, GenerationJob } from '../../api/types';
import { ShotCard } from './ShotCard';
import {
  Plus,
  Edit2,
  Archive,
  Check,
  X,
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

const dialogueToText = (dialogue: unknown): string => {
  if (typeof dialogue === 'string') return dialogue;
  if (dialogue == null) return '';
  try {
    return JSON.stringify(dialogue, null, 2);
  } catch {
    return String(dialogue);
  }
};

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
  const [description, setDescription] = useState(scene.description || '');
  const [purpose, setPurpose] = useState(scene.purpose || '');
  const [narration, setNarration] = useState(scene.narration || '');
  const [dialogue, setDialogue] = useState(dialogueToText(scene.dialogue));
  const [durationSeconds, setDurationSeconds] = useState(scene.duration_seconds || 5);

  const resetEditor = () => {
    setHeading(scene.heading || `Scene ${scene.scene_number}`);
    setSetting(scene.setting || '');
    setDescription(scene.description || '');
    setPurpose(scene.purpose || '');
    setNarration(scene.narration || '');
    setDialogue(dialogueToText(scene.dialogue));
    setDurationSeconds(scene.duration_seconds || 5);
  };

  const handleSaveScene = () => {
    onUpdateScene(scene.id, {
      heading,
      setting,
      description: description || undefined,
      purpose: purpose || undefined,
      narration: narration || undefined,
      dialogue: dialogue || undefined,
      duration_seconds: durationSeconds,
    });
    setIsEditing(false);
  };

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
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '12px',
          paddingBottom: '14px',
          borderBottom: '1px solid var(--border-subtle)',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', flex: 1, minWidth: '320px' }}>
          <Clapperboard size={18} color="#818cf8" style={{ marginTop: '4px' }} />
          {isEditing ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, maxWidth: '720px' }} data-testid={`scene-editor-${scene.id}`}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 110px', gap: '8px' }}>
                <input
                  type="text"
                  value={heading}
                  onChange={(e) => setHeading(e.target.value)}
                  placeholder="Scene Heading (e.g. INT. COMMAND CENTER - NIGHT)"
                  data-testid={`scene-heading-input-${scene.id}`}
                />
                <input
                  type="text"
                  value={setting}
                  onChange={(e) => setSetting(e.target.value)}
                  placeholder="Setting / location"
                />
                <input
                  type="number"
                  min="0.5"
                  step="0.5"
                  value={durationSeconds}
                  onChange={(e) => setDurationSeconds(Number(e.target.value))}
                  title="Scene duration seconds"
                />
              </div>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Scene description / visual situation"
                data-testid={`scene-description-input-${scene.id}`}
              />
              <input
                type="text"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="Scene purpose / narrative objective"
              />
              <textarea
                rows={2}
                value={narration}
                onChange={(e) => setNarration(e.target.value)}
                placeholder="Narration / VO text (optional)"
                data-testid={`scene-narration-input-${scene.id}`}
              />
              <textarea
                rows={2}
                value={dialogue}
                onChange={(e) => setDialogue(e.target.value)}
                placeholder="Dialogue / speaker lines (optional)"
                data-testid={`scene-dialogue-input-${scene.id}`}
              />
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button
                  className="btn btn-xs btn-outline"
                  onClick={() => {
                    resetEditor();
                    setIsEditing(false);
                  }}
                  title="Cancel scene edits"
                >
                  <X size={12} /> Cancel
                </button>
                <button className="btn btn-xs btn-primary" onClick={handleSaveScene} data-testid={`scene-save-btn-${scene.id}`}>
                  <Check size={14} /> Save Scene
                </button>
              </div>
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
              {scene.description && (
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '5px', maxWidth: '720px' }}>
                  {scene.description}
                </p>
              )}
              {scene.narration && (
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  VO: {scene.narration}
                </p>
              )}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          {canMoveSceneUp && onMoveSceneUp && (
            <button className="btn btn-xs btn-outline" onClick={() => onMoveSceneUp(scene.id)} title="Move Scene Up">
              <ChevronUp size={12} />
            </button>
          )}
          {canMoveSceneDown && onMoveSceneDown && (
            <button className="btn btn-xs btn-outline" onClick={() => onMoveSceneDown(scene.id)} title="Move Scene Down">
              <ChevronDown size={12} />
            </button>
          )}
          {onDuplicateScene && (
            <button className="btn btn-xs btn-secondary" onClick={() => onDuplicateScene(scene.id)} title="Duplicate Scene (and shots)" data-testid={`duplicate-scene-${scene.id}`}>
              <Copy size={12} /> Duplicate
            </button>
          )}
          <button className="btn btn-xs btn-outline" onClick={() => onToggleSceneLock(scene)} title={scene.is_locked ? 'Unlock Scene' : 'Lock Scene'}>
            {scene.is_locked ? <Unlock size={12} /> : <Lock size={12} />}
            {scene.is_locked ? 'Unlock' : 'Lock'}
          </button>
          {!isEditing && (
            <button
              className="btn btn-xs btn-secondary"
              onClick={() => {
                resetEditor();
                setIsEditing(true);
              }}
              disabled={scene.is_locked}
              title="Edit Scene narrative fields"
              data-testid={`edit-scene-btn-${scene.id}`}
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
          <button className="btn btn-sm btn-primary" onClick={() => onAddShot(scene.id)} disabled={scene.is_locked} data-testid={`add-shot-btn-${scene.id}`}>
            <Plus size={14} /> Add Shot
          </button>
        </div>
      </div>

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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '16px' }}>
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
              onToggleSelect={onToggleSelectShot ? (e) => { e.stopPropagation(); onToggleSelectShot(shot.id); } : undefined}
              onMoveUp={onMoveShotUp ? (e) => { e.stopPropagation(); onMoveShotUp(scene.id, shot.id); } : undefined}
              onMoveDown={onMoveShotDown ? (e) => { e.stopPropagation(); onMoveShotDown(scene.id, shot.id); } : undefined}
              onToggleLock={(e) => { e.stopPropagation(); onToggleShotLock(shot); }}
            />
          ))}
        </div>
      )}
    </div>
  );
};
