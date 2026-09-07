import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import type { ExportPreset, RenderBatch } from '../../api/types';

interface ExportPresetsModalProps {
  projectId: string;
  onClose: () => void;
}

export const ExportPresetsModal: React.FC<ExportPresetsModalProps> = ({
  projectId,
  onClose,
}) => {
  const [presets, setPresets] = useState<ExportPreset[]>([]);
  const [selectedPresetIds, setSelectedPresetIds] = useState<string[]>([
    'YT_STANDARD_1080P',
    'TIKTOK_REELS_9X16',
  ]);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeBatch, setActiveBatch] = useState<RenderBatch | null>(null);

  useEffect(() => {
    loadPresets();
  }, [projectId]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (activeBatch && activeBatch.status === 'PROCESSING') {
      timer = setInterval(async () => {
        try {
          const updated = await api.getRenderBatch(projectId, activeBatch.id);
          setActiveBatch(updated);
          if (updated.status !== 'PROCESSING') {
            clearInterval(timer);
          }
        } catch (err) {
          // ignore transient poll error
        }
      }, 3000);
    }
    return () => clearInterval(timer);
  }, [projectId, activeBatch?.id, activeBatch?.status]);

  const loadPresets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listExportPresets(projectId);
      setPresets(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load export presets');
    } finally {
      setLoading(false);
    }
  };

  const togglePreset = (presetId: string) => {
    setSelectedPresetIds((prev) =>
      prev.includes(presetId)
        ? prev.filter((id) => id !== presetId)
        : [...prev, presetId]
    );
  };

  const totalEstimatedCost = presets
    .filter((p) => selectedPresetIds.includes(p.preset_id))
    .reduce((sum, p) => sum + p.estimated_cost_usd, 0);

  const handleSubmitBatch = async () => {
    if (selectedPresetIds.length === 0) return;
    try {
      setSubmitting(true);
      setError(null);
      const batch = await api.submitExportBatch(projectId, {
        preset_ids: selectedPresetIds,
      });
      setActiveBatch(batch);
    } catch (err: any) {
      setError(err.message || 'Failed to submit export batch');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: '#1e1e2e',
          color: '#cdd6f4',
          padding: '24px',
          borderRadius: '12px',
          width: '560px',
          maxWidth: '90vw',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          border: '1px solid #313244',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#f5e0dc' }}>
            🎬 Export & Platform Presets
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#a6adc8',
              fontSize: '1.25rem',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        </div>

        {error && (
          <div
            style={{
              backgroundColor: 'rgba(243, 139, 168, 0.15)',
              border: '1px solid #f38ba8',
              color: '#f38ba8',
              padding: '10px 14px',
              borderRadius: '6px',
              marginBottom: '16px',
              fontSize: '0.875rem',
            }}
          >
            ⚠️ {error}
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '32px 0', color: '#a6adc8' }}>
            Loading export presets...
          </div>
        ) : activeBatch ? (
          <div>
            <div
              style={{
                backgroundColor: '#181825',
                padding: '14px',
                borderRadius: '8px',
                marginBottom: '16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 'bold' }}>Batch Status:</span>
                <span
                  style={{
                    color:
                      activeBatch.status === 'COMPLETED'
                        ? '#a6e3a1'
                        : activeBatch.status === 'FAILED'
                        ? '#f38ba8'
                        : '#f9e2af',
                    fontWeight: 'bold',
                  }}
                >
                  {activeBatch.status}
                </span>
              </div>
              <div style={{ fontSize: '0.875rem', color: '#bac2de' }}>
                Progress: {activeBatch.completed_variants + activeBatch.failed_variants} / {activeBatch.total_variants} completed
              </div>
            </div>

            {activeBatch.child_jobs && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                {activeBatch.child_jobs.map((job) => (
                  <div
                    key={job.id}
                    style={{
                      backgroundColor: '#26283b',
                      padding: '10px 14px',
                      borderRadius: '6px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: '600' }}>{job.render_profile}</div>
                      <div style={{ fontSize: '0.75rem', color: '#a6adc8' }}>
                        Key: {job.render_variant_key}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span
                        style={{
                          fontSize: '0.85rem',
                          color:
                            job.status === 'COMPLETED'
                              ? '#a6e3a1'
                              : job.status === 'FAILED'
                              ? '#f38ba8'
                              : '#89b4fa',
                        }}
                      >
                        {job.status} ({Math.round(job.progress)}%)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={() => setActiveBatch(null)}
                style={{
                  backgroundColor: '#313244',
                  color: '#cdd6f4',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                New Export
              </button>
              <button
                onClick={onClose}
                style={{
                  backgroundColor: '#89b4fa',
                  color: '#11111b',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                }}
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: '0.875rem', color: '#bac2de', marginBottom: '14px' }}>
              Select target platform presets to export concurrently from your approved timeline:
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              {presets.map((preset) => {
                const isSelected = selectedPresetIds.includes(preset.preset_id);
                return (
                  <div
                    key={preset.preset_id}
                    onClick={() => togglePreset(preset.preset_id)}
                    style={{
                      backgroundColor: isSelected ? '#2a2b3d' : '#181825',
                      border: `1px solid ${isSelected ? '#89b4fa' : '#313244'}`,
                      padding: '12px 14px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                        style={{ cursor: 'pointer', accentColor: '#89b4fa' }}
                      />
                      <div>
                        <div style={{ fontWeight: 'bold', color: '#cdd6f4' }}>
                          {preset.target_platform} ({preset.aspect_ratio})
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#a6adc8' }}>
                          {preset.width}x{preset.height} • {preset.video_codec.toUpperCase()} •{' '}
                          {Math.round(preset.video_bitrate_kbps / 1000)} Mbps
                        </div>
                      </div>
                    </div>
                    <div style={{ fontWeight: '600', color: '#a6e3a1', fontSize: '0.9rem' }}>
                      ${preset.estimated_cost_usd.toFixed(2)}
                    </div>
                  </div>
                );
              })}
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: '#181825',
                padding: '12px 16px',
                borderRadius: '8px',
                marginBottom: '20px',
              }}
            >
              <div>
                <span style={{ fontSize: '0.875rem', color: '#a6adc8' }}>Total Estimated Batch Cost:</span>
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#a6e3a1' }}>
                ${totalEstimatedCost.toFixed(2)} USD
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={onClose}
                style={{
                  backgroundColor: '#313244',
                  color: '#cdd6f4',
                  border: 'none',
                  padding: '10px 18px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitBatch}
                disabled={selectedPresetIds.length === 0 || submitting}
                style={{
                  backgroundColor: selectedPresetIds.length === 0 ? '#45475a' : '#89b4fa',
                  color: selectedPresetIds.length === 0 ? '#7f849c' : '#11111b',
                  border: 'none',
                  padding: '10px 20px',
                  borderRadius: '6px',
                  fontWeight: 'bold',
                  cursor: selectedPresetIds.length === 0 || submitting ? 'not-allowed' : 'pointer',
                }}
              >
                {submitting
                  ? 'Authorizing Batch...'
                  : `Confirm & Export (${selectedPresetIds.length} Variants)`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
