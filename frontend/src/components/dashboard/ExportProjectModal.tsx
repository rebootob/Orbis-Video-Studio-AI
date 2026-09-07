import React, { useState } from 'react';
import type { Project } from '../../api/types';
import { apiClient } from '../../api/client';
import { X, Package, Download, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface ExportProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: Project | null;
}

export const ExportProjectModal: React.FC<ExportProjectModalProps> = ({
  isOpen,
  onClose,
  project,
}) => {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen || !project) return null;

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    setSuccess(false);

    try {
      const blob = await apiClient.exportProjectArchive(project.id, {
        package_type: 'FULL_SELF_CONTAINED',
        include_history: true,
        include_renders: true,
      });

      // Trigger browser download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const slug = (project.title || 'project').toLowerCase().replace(/[^\w\s-]/g, '').replace(/[-\s]+/g, '-');
      a.download = `${slug}_${project.id.slice(0, 8)}.orbis`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setSuccess(true);
      setTimeout(() => {
        onClose();
        setSuccess(false);
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to export project archive.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} data-testid="export-project-modal">
      <div
        className="modal-dialog"
        style={{ maxWidth: '520px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Package size={18} color="#818cf8" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: '600' }}>Export Project Archive (.orbis)</h2>
          </div>
          <button className="btn btn-xs btn-outline" onClick={onClose} disabled={exporting}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {error && (
            <div className="alert alert-danger" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem' }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="alert alert-success" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', backgroundColor: '#064e3b', color: '#6ee7b7' }}>
              <CheckCircle2 size={16} />
              <span>Archive generated and download initiated!</span>
            </div>
          )}

          <div style={{ padding: '12px', background: '#1e293b', borderRadius: '6px', border: '1px solid #334155' }}>
            <div style={{ fontWeight: '600', color: '#f8fafc', marginBottom: '4px' }}>{project.title}</div>
            <div style={{ fontSize: '0.8125rem', color: '#94a3b8', display: 'flex', gap: '16px' }}>
              <span>Mode: <strong>{project.video_mode}</strong></span>
              <span>Scenes: <strong>{project.scene_count || 0}</strong></span>
              <span>Shots: <strong>{project.shot_count || 0}</strong></span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontSize: '0.875rem', fontWeight: '500', color: '#e2e8f0' }}>Package Contents (Core V1 FULL_SELF_CONTAINED)</div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '0.8125rem', color: '#cbd5e1' }} data-testid="package-content-history">
              <CheckCircle2 size={16} color="#34d399" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: '500', color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>Historical Revisions & Audits</span>
                  <span style={{ fontSize: '0.6875rem', padding: '1px 6px', background: '#064e3b', color: '#6ee7b7', borderRadius: '4px' }}>Included</span>
                </div>
                <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginTop: '2px' }}>
                  Preserves audit trails, story versions, generation and render history, and usage ledgers bit-for-bit.
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '0.8125rem', color: '#cbd5e1' }} data-testid="package-content-renders">
              <CheckCircle2 size={16} color="#34d399" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: '500', color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>Rendered Outputs & Media Binaries</span>
                  <span style={{ fontSize: '0.6875rem', padding: '1px 6px', background: '#064e3b', color: '#6ee7b7', borderRadius: '4px' }}>Included</span>
                </div>
                <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginTop: '2px' }}>
                  Includes rendered video files, audio tracks, keyframes, and asset binaries from storage.
                </div>
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.75rem', color: '#64748b', borderTop: '1px solid #334155', paddingTop: '10px' }}>
            Archive format version 1.0.0 (RFC 8785 canonical JSON checksums with sha256 non-circular trust root). Secrets and API keys are automatically stripped.
          </div>
        </div>

        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button className="btn btn-outline" onClick={onClose} disabled={exporting}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            data-testid="export-submit-btn"
            onClick={handleExport}
            disabled={exporting || success}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            {exporting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Exporting Archive...</span>
              </>
            ) : (
              <>
                <Download size={16} />
                <span>Export (.orbis)</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
