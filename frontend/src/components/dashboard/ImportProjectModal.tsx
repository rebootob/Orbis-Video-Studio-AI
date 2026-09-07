import React, { useState, useRef } from 'react';
import type { ProjectValidationResult, ProjectImportResult } from '../../api/types';
import { apiClient } from '../../api/client';
import {
  X,
  Upload,
  FileCheck,
  AlertTriangle,
  AlertCircle,
  Copy,
  RotateCcw,
  CheckCircle2,
  Loader2,
  ArrowRight,
} from 'lucide-react';

interface ImportProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess: (projectId: string) => void;
}

export const ImportProjectModal: React.FC<ImportProjectModalProps> = ({
  isOpen,
  onClose,
  onImportSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ProjectValidationResult | null>(null);
  const [importMode, setImportMode] = useState<'CLONE' | 'RESTORE'>('CLONE');
  const [overrideTitle, setOverrideTitle] = useState('');
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<ProjectImportResult | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileSelect = async (selectedFile: File) => {
    if (!selectedFile.name.toLowerCase().endsWith('.orbis') && !selectedFile.name.toLowerCase().endsWith('.zip')) {
      setError('Please select a valid .orbis archive file.');
      return;
    }

    setFile(selectedFile);
    setError(null);
    setValidationResult(null);
    setValidating(true);

    try {
      const result = await apiClient.validateProjectArchive(selectedFile);
      setValidationResult(result);
      setOverrideTitle(`${result.title} (Imported)`);
      if (!result.collision_detected && result.allowed_modes.includes('RESTORE')) {
        setImportMode('CLONE'); // Still default to CLONE as recommended
      } else {
        setImportMode('CLONE');
      }
    } catch (err: any) {
      setError(err.message || 'Validation failed for the uploaded archive.');
    } finally {
      setValidating(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleExecuteImport = async () => {
    if (!file || !validationResult) return;

    setImporting(true);
    setError(null);

    try {
      const result = await apiClient.executeProjectImport(
        file,
        importMode,
        importMode === 'CLONE' && overrideTitle.trim() ? overrideTitle.trim() : undefined
      );
      setSuccessResult(result);
    } catch (err: any) {
      setError(err.message || 'Failed to execute project import.');
    } finally {
      setImporting(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setValidationResult(null);
    setSuccessResult(null);
    setError(null);
    setOverrideTitle('');
    setImportMode('CLONE');
  };

  return (
    <div className="modal-backdrop" onClick={onClose} data-testid="import-project-modal">
      <div
        className="modal-dialog"
        style={{ maxWidth: '620px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Upload size={18} color="#38bdf8" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: '600' }}>Import Project Archive (.orbis)</h2>
          </div>
          <button className="btn btn-xs btn-outline" onClick={onClose} disabled={importing}>
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

          {successResult ? (
            /* Success View */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', alignItems: 'center', textAlign: 'center', padding: '16px 0' }}>
              <CheckCircle2 size={48} color="#34d399" />
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#f8fafc', marginBottom: '4px' }}>
                  Project Imported Successfully!
                </h3>
                <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
                  {successResult.title} has been imported in <strong>{successResult.import_mode}</strong> mode with {successResult.imported_asset_count} assets.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => {
                    onClose();
                    onImportSuccess(successResult.project_id);
                  }}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <span>Open Project Workspace</span>
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          ) : !validationResult ? (
            /* Upload / Dropzone View */
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: '2px dashed #475569',
                borderRadius: '8px',
                padding: '40px 20px',
                textAlign: 'center',
                cursor: validating ? 'wait' : 'pointer',
                background: '#1e293b',
                transition: 'border-color 0.2s',
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".orbis,.zip"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileSelect(e.target.files[0]);
                  }
                }}
              />
              {validating ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                  <Loader2 size={36} color="#38bdf8" className="animate-spin" />
                  <div style={{ color: '#e2e8f0', fontWeight: '500' }}>Validating archive security & checksums...</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Checking ZIP integrity, paths, and trust root</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                  <Upload size={36} color="#94a3b8" />
                  <div>
                    <div style={{ color: '#f8fafc', fontWeight: '500', marginBottom: '2px' }}>
                      Drag & Drop .orbis project archive here
                    </div>
                    <div style={{ color: '#94a3b8', fontSize: '0.8125rem' }}>or click to browse your files</div>
                  </div>
                  <div style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '4px' }}>
                    Maximum 10GB archive size supported
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Validation Summary & Mode Selection */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ padding: '12px', background: '#1e293b', borderRadius: '6px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontWeight: '600' }}>
                    <FileCheck size={16} />
                    <span>{validationResult.title}</span>
                  </div>
                  <span style={{ fontSize: '0.75rem', background: '#334155', padding: '2px 6px', borderRadius: '4px', color: '#cbd5e1' }}>
                    v{validationResult.archive_format_version}
                  </span>
                </div>
                <div style={{ fontSize: '0.8125rem', color: '#94a3b8', display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
                  <span>Mode: <strong>{validationResult.video_mode}</strong></span>
                  <span>Scenes: <strong>{validationResult.entity_counts.scenes || 0}</strong></span>
                  <span>Shots: <strong>{validationResult.entity_counts.shots || 0}</strong></span>
                  <span>Assets: <strong>{validationResult.entity_counts.assets || 0}</strong></span>
                </div>
              </div>

              {validationResult.collision_detected && (
                <div className="alert alert-warning" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', background: '#451a03', color: '#fcd34d', border: '1px solid #78350f' }}>
                  <AlertTriangle size={16} />
                  <span>A project with original ID already exists in this database. RESTORE mode is disabled to prevent data corruption.</span>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ fontSize: '0.875rem', fontWeight: '500', color: '#e2e8f0' }}>Select Import Mode</div>

                {/* Option 1: CLONE */}
                <div
                  onClick={() => setImportMode('CLONE')}
                  style={{
                    padding: '12px',
                    borderRadius: '6px',
                    border: `1px solid ${importMode === 'CLONE' ? '#38bdf8' : '#334155'}`,
                    background: importMode === 'CLONE' ? '#0c4a6e22' : '#1e293b',
                    cursor: 'pointer',
                    display: 'flex',
                    gap: '10px',
                  }}
                >
                  <Copy size={20} color={importMode === 'CLONE' ? '#38bdf8' : '#94a3b8'} style={{ marginTop: '2px' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: '600', color: '#f8fafc', fontSize: '0.875rem' }}>Clone as New Project</span>
                      <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: '500' }}>Recommended</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                      Generates fresh UUIDs and storage keys for all entities while retaining original project lineage. Completely safe against ID collisions.
                    </div>
                    {importMode === 'CLONE' && (
                      <div style={{ marginTop: '8px' }}>
                        <label style={{ display: 'block', fontSize: '0.75rem', color: '#cbd5e1', marginBottom: '2px' }}>Project Title</label>
                        <input
                          type="text"
                          className="form-control"
                          value={overrideTitle}
                          onChange={(e) => setOverrideTitle(e.target.value)}
                          placeholder="Project title"
                          style={{ fontSize: '0.8125rem', width: '100%', padding: '4px 8px', background: '#0f172a', border: '1px solid #475569', borderRadius: '4px', color: '#f8fafc' }}
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Option 2: RESTORE */}
                <div
                  onClick={() => {
                    if (!validationResult.collision_detected && validationResult.allowed_modes.includes('RESTORE')) {
                      setImportMode('RESTORE');
                    }
                  }}
                  style={{
                    padding: '12px',
                    borderRadius: '6px',
                    border: `1px solid ${importMode === 'RESTORE' ? '#38bdf8' : '#334155'}`,
                    background: importMode === 'RESTORE' ? '#0c4a6e22' : '#1e293b',
                    cursor: validationResult.collision_detected ? 'not-allowed' : 'pointer',
                    opacity: validationResult.collision_detected ? 0.5 : 1,
                    display: 'flex',
                    gap: '10px',
                  }}
                >
                  <RotateCcw size={20} color={importMode === 'RESTORE' ? '#38bdf8' : '#94a3b8'} style={{ marginTop: '2px' }} />
                  <div>
                    <span style={{ fontWeight: '600', color: '#f8fafc', fontSize: '0.875rem' }}>Restore Original Project</span>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                      Preserves exact original UUIDs and references. Only available on a clean database without existing project ID collisions.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {validationResult && !successResult ? (
            <button className="btn btn-xs btn-outline" onClick={handleReset} disabled={importing}>
              Choose Different File
            </button>
          ) : (
            <div />
          )}

          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-outline" onClick={onClose} disabled={importing}>
              {successResult ? 'Close' : 'Cancel'}
            </button>
            {validationResult && !successResult && (
              <button
                className="btn btn-primary"
                onClick={handleExecuteImport}
                disabled={importing || (importMode === 'CLONE' && !overrideTitle.trim())}
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                {importing ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Importing Project...</span>
                  </>
                ) : (
                  <>
                    <Upload size={16} />
                    <span>Execute Import</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
