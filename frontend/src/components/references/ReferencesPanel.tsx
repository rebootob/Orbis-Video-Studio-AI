import React, { useState, useEffect, useRef } from 'react';
import type { ReferenceItem, AssetUploadResponse } from '../../api/types';
import { api } from '../../api/client';
import {
  BookOpen,
  User,
  MapPin,
  Palette,
  Award,
  Plus,
  Lock,
  Unlock,
  Upload,
  FileText,
  File,
} from 'lucide-react';

interface ReferencesPanelProps {
  references: ReferenceItem[];
  projectId: string;
  onAddCharacter: (data: { name: string; backstory?: string }) => Promise<void>;
  onAddLocation: (data: { name: string; setting_notes?: string }) => Promise<void>;
  onAddStyle: (data: { name: string; style_prompt_prefix?: string }) => Promise<void>;
  onAddBrand: (data: { name: string; guidelines?: string }) => Promise<void>;
  onToggleLock: (item: ReferenceItem) => Promise<void>;
}

export const ReferencesPanel: React.FC<ReferencesPanelProps> = ({
  references,
  projectId,
  onAddCharacter,
  onAddLocation,
  onAddStyle,
  onAddBrand,
  onToggleLock,
}) => {
  const [activeCategory, setActiveCategory] = useState<
    'CHARACTER' | 'LOCATION' | 'STYLE' | 'BRAND' | 'DOCUMENTS'
  >('CHARACTER');
  const [showAddModal, setShowAddModal] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  // Uploaded Assets state
  const [assets, setAssets] = useState<AssetUploadResponse[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadAssets = async () => {
    if (!projectId) return;
    try {
      const list = await api.listProjectAssets(projectId);
      setAssets(list);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadAssets();
  }, [projectId]);

  const filteredReferences = references.filter(
    (r) => r.reference_type === activeCategory
  );

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !projectId) return;

    try {
      setUploading(true);
      setUploadError(null);
      await api.uploadAsset(projectId, file, 'DOCUMENT', file.name);
      await loadAssets();
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      setSaving(true);
      if (activeCategory === 'CHARACTER') {
        await onAddCharacter({ name: name.trim(), backstory: description });
      } else if (activeCategory === 'LOCATION') {
        await onAddLocation({ name: name.trim(), setting_notes: description });
      } else if (activeCategory === 'STYLE') {
        await onAddStyle({ name: name.trim(), style_prompt_prefix: description });
      } else if (activeCategory === 'BRAND') {
        await onAddBrand({ name: name.trim(), guidelines: description });
      }
      setName('');
      setDescription('');
      setShowAddModal(false);
    } catch (err: any) {
      alert(`Failed to save reference: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        padding: '20px',
      }}
      data-testid="references-panel"
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BookOpen size={20} color="#818cf8" />
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
              Continuity Bibles & References
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Persistent character traits, location settings, visual styles, brand bibles, and source documents
            </p>
          </div>
        </div>

        {activeCategory === 'DOCUMENTS' ? (
          <div>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            <button
              className="btn btn-primary btn-sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              data-testid="upload-document-btn"
            >
              <Upload size={14} /> {uploading ? 'Uploading...' : 'Upload Document'}
            </button>
          </div>
        ) : (
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowAddModal(true)}
            data-testid="add-reference-btn"
          >
            <Plus size={14} /> Add {activeCategory.toLowerCase()}
          </button>
        )}
      </div>

      {uploadError && (
        <div className="alert alert-danger" style={{ marginBottom: '16px', fontSize: '0.8125rem' }}>
          {uploadError}
        </div>
      )}

      {/* Category Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '20px',
          borderBottom: '1px solid var(--border-default)',
          paddingBottom: '8px',
          overflowX: 'auto',
        }}
      >
        {[
          { key: 'CHARACTER', label: 'Characters', icon: <User size={14} /> },
          { key: 'LOCATION', label: 'Locations', icon: <MapPin size={14} /> },
          { key: 'STYLE', label: 'Visual Styles', icon: <Palette size={14} /> },
          { key: 'BRAND', label: 'Brand Bibles', icon: <Award size={14} /> },
          { key: 'DOCUMENTS', label: 'Documents & Media', icon: <FileText size={14} /> },
        ].map((tab) => (
          <button
            key={tab.key}
            className={`btn btn-sm ${
              activeCategory === tab.key ? 'btn-primary' : 'btn-secondary'
            }`}
            onClick={() => setActiveCategory(tab.key as any)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Documents & Media Category */}
      {activeCategory === 'DOCUMENTS' ? (
        assets.length === 0 ? (
          <div
            style={{
              padding: '48px 20px',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.875rem',
            }}
          >
            No source documents or reference media uploaded yet. Click &quot;Upload Document&quot; above to ingest briefs, scripts, or images.
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '16px',
            }}
          >
            {assets.map((asset) => (
              <div
                key={asset.id}
                className="card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '10px',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <File size={16} color="#818cf8" />
                    <h4 style={{ fontSize: '0.9375rem', fontWeight: 600 }}>{asset.original_filename}</h4>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Type: {asset.asset_type} • {asset.file_size_bytes ? `${Math.round(asset.file_size_bytes / 1024)} KB` : 'Unknown size'}
                  </div>
                </div>

                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'var(--text-muted)',
                    borderTop: '1px solid var(--border-subtle)',
                    paddingTop: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <span>Uploaded {new Date(asset.created_at).toLocaleDateString()}</span>
                  <span className="badge badge-approved" style={{ fontSize: '0.65rem' }}>Stored</span>
                </div>
              </div>
            ))}
          </div>
        )
      ) : filteredReferences.length === 0 ? (
        <div
          style={{
            padding: '48px 20px',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.875rem',
          }}
        >
          No {activeCategory.toLowerCase()} bibles added yet. Click &quot;+ Add&quot; above to define persistent continuity.
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '16px',
          }}
        >
          {filteredReferences.map((item) => (
            <div
              key={item.id}
              className="card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '10px',
              }}
              data-testid={`reference-card-${item.id}`}
            >
              <div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '6px',
                  }}
                >
                  <h4 style={{ fontSize: '0.9375rem', fontWeight: 600 }}>{item.name}</h4>
                  <button
                    className={`btn btn-xs ${item.is_locked ? 'btn-danger' : 'btn-outline'}`}
                    onClick={() => onToggleLock(item)}
                    title={item.is_locked ? 'Unlock item' : 'Lock item'}
                  >
                    {item.is_locked ? <Lock size={12} /> : <Unlock size={12} />}
                  </button>
                </div>

                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  {item.description || '(No description provided)'}
                </p>
              </div>

              <div
                style={{
                  fontSize: '0.7rem',
                  color: 'var(--text-muted)',
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>Type: {item.reference_type}</span>
                {item.is_locked && <span style={{ color: 'var(--accent-rose)' }}>Locked</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Reference Modal */}
      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div
            className="modal-dialog"
            style={{ maxWidth: '460px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
                Add New {activeCategory}
              </h3>
              <button className="btn btn-xs btn-outline" onClick={() => setShowAddModal(false)}>
                &times;
              </button>
            </div>
            <form onSubmit={handleSave}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Name *</label>
                  <input
                    type="text"
                    required
                    placeholder={`e.g. ${
                      activeCategory === 'CHARACTER'
                        ? 'Captain Sarah'
                        : activeCategory === 'LOCATION'
                        ? 'Neo-Tokyo Rooftop'
                        : activeCategory === 'STYLE'
                        ? 'Cyberpunk Neon Noir'
                        : 'Nike ACG'
                    }`}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">
                    {activeCategory === 'CHARACTER'
                      ? 'Backstory & Visual Traits'
                      : activeCategory === 'LOCATION'
                      ? 'Setting Notes & Environment'
                      : activeCategory === 'STYLE'
                      ? 'Style Prompt Prefix'
                      : 'Brand Guidelines'}
                  </label>
                  <textarea
                    rows={4}
                    placeholder="Provide details for generative continuity..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : 'Add Reference'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
