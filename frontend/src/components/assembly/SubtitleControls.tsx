import React, { useCallback, useEffect, useState } from 'react';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

type SubtitleSegment = {
  id: string;
  ordinal: number;
  text: string;
  start_time: number;
  end_time: number;
  language: string;
  source_type: string;
  source_ref: string;
};

type SubtitleTrack = {
  id: string;
  version_number: number;
  timeline_version: number;
  language: string;
  enabled: boolean;
  render_mode: 'OFF' | 'BURN_IN';
  review_status: string;
  is_reviewed: boolean;
  is_stale: boolean;
  segments: SubtitleSegment[];
  srt_sha256: string;
};

interface SubtitleControlsProps {
  projectId: string;
}

async function jsonRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Keep status fallback.
    }
    throw new Error(detail);
  }
  return response.json();
}

export const SubtitleControls: React.FC<SubtitleControlsProps> = ({ projectId }) => {
  const [track, setTrack] = useState<SubtitleTrack | null>(null);
  const [language, setLanguage] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const active = await jsonRequest<SubtitleTrack | null>(`/projects/${projectId}/subtitles/active`);
      setTrack(active);
      if (active?.language && active.language !== 'und') setLanguage(active.language);
    } catch (err: any) {
      setError(err.message || 'Failed to load subtitles');
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const generate = async () => {
    try {
      setBusy('generate');
      setError(null);
      const generated = await jsonRequest<SubtitleTrack>(`/projects/${projectId}/subtitles/generate`, {
        method: 'POST',
        body: JSON.stringify({ language: language.trim() || null }),
      });
      setTrack(generated);
    } catch (err: any) {
      setError(err.message || 'Subtitle generation failed');
    } finally {
      setBusy(null);
    }
  };

  const review = async (renderMode: 'OFF' | 'BURN_IN') => {
    try {
      setBusy(renderMode);
      setError(null);
      const reviewed = await jsonRequest<SubtitleTrack>(`/projects/${projectId}/subtitles/review`, {
        method: 'POST',
        body: JSON.stringify({ enabled: renderMode === 'BURN_IN', render_mode: renderMode }),
      });
      setTrack(reviewed);
    } catch (err: any) {
      setError(err.message || 'Subtitle review failed');
    } finally {
      setBusy(null);
    }
  };

  const downloadSrt = async () => {
    try {
      setBusy('download');
      setError(null);
      const response = await fetch(`${BASE_URL}/projects/${projectId}/subtitles/srt`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `SRT export failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `orbis_subtitles_v${track?.timeline_version || 1}.srt`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || 'SRT export failed');
    } finally {
      setBusy(null);
    }
  };

  return (
    <section
      data-testid="subtitle-controls"
      style={{
        backgroundColor: '#181825',
        border: '1px solid #313244',
        borderRadius: '8px',
        padding: '14px',
        marginBottom: '18px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '10px' }}>
        <div>
          <div style={{ fontWeight: 700, color: '#f5e0dc' }}>💬 Subtitle Review & Burn-in</div>
          <div style={{ fontSize: '0.75rem', color: '#a6adc8', marginTop: '3px' }}>
            Deterministic subtitles from existing VO/dialogue/narration. No speech-to-text provider is used.
          </div>
        </div>
        {track && (
          <span style={{ fontSize: '0.75rem', color: track.is_stale ? '#f9e2af' : '#a6e3a1' }}>
            {track.is_stale ? 'STALE — regenerate' : `v${track.version_number} • ${track.review_status}`}
          </span>
        )}
      </div>

      {error && (
        <div style={{ color: '#f38ba8', fontSize: '0.8rem', marginBottom: '10px' }}>⚠️ {error}</div>
      )}

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '10px' }}>
        <input
          aria-label="Subtitle language"
          placeholder="Language e.g. th"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          style={{
            background: '#11111b',
            border: '1px solid #45475a',
            color: '#cdd6f4',
            borderRadius: '6px',
            padding: '7px 9px',
            width: '140px',
          }}
        />
        <button onClick={generate} disabled={busy !== null} style={buttonStyle('#89b4fa')}>
          {busy === 'generate' ? 'Generating…' : track ? 'Regenerate' : 'Generate'}
        </button>
        <button
          onClick={() => review('BURN_IN')}
          disabled={!track || track.is_stale || busy !== null}
          style={buttonStyle('#a6e3a1')}
        >
          Approve & Burn In
        </button>
        <button
          onClick={() => review('OFF')}
          disabled={!track || track.is_stale || busy !== null}
          style={buttonStyle('#f9e2af')}
        >
          Approve / Subtitle Off
        </button>
        <button
          onClick={downloadSrt}
          disabled={!track || track.is_stale || busy !== null}
          style={buttonStyle('#cba6f7')}
        >
          Download SRT
        </button>
      </div>

      {track && (
        <>
          <div style={{ fontSize: '0.75rem', color: '#bac2de', marginBottom: '8px' }}>
            Render: <strong>{track.enabled ? track.render_mode : 'OFF'}</strong> • Language: {track.language} • {track.segments.length} segments
          </div>
          <div style={{ maxHeight: '145px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {track.segments.map((segment) => (
              <div key={segment.id} style={{ background: '#26283b', borderRadius: '5px', padding: '7px 9px', fontSize: '0.78rem' }}>
                <span style={{ color: '#89b4fa', marginRight: '8px' }}>
                  {formatTime(segment.start_time)}–{formatTime(segment.end_time)}
                </span>
                <span style={{ color: '#cdd6f4' }}>{segment.text}</span>
                <div style={{ color: '#6c7086', fontSize: '0.65rem', marginTop: '2px' }}>{segment.source_ref}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
};

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(1).padStart(4, '0');
  return `${mins}:${secs}`;
}

function buttonStyle(backgroundColor: string): React.CSSProperties {
  return {
    backgroundColor,
    color: '#11111b',
    border: 'none',
    borderRadius: '6px',
    padding: '7px 10px',
    fontWeight: 700,
    fontSize: '0.75rem',
    cursor: 'pointer',
  };
}
