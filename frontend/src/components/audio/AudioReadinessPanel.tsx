import React from 'react';
import { Volume2, Mic, Music, Sparkles, Wind, Sliders } from 'lucide-react';

interface AudioReadinessPanelProps {
  projectId: string;
}

export const AudioReadinessPanel: React.FC<AudioReadinessPanelProps> = () => {
  const audioStems = [
    {
      id: 'vo',
      name: 'Voiceover (VO) / Dialogue Stem',
      icon: <Mic size={18} color="#818cf8" />,
      status: 'Architectural Allocation Ready',
      desc: 'Schema track slot allocated to receive synthesized narration or recorded speech once audio provider is integrated.',
    },
    {
      id: 'bgm',
      name: 'Background Score / Music Track',
      icon: <Music size={18} color="#fbbf24" />,
      status: 'Timing Alignment Ready',
      desc: 'Music track blueprint mapped to total shot timeline and cut markers.',
    },
    {
      id: 'sfx',
      name: 'Sound Effects (SFX)',
      icon: <Sparkles size={18} color="#34d399" />,
      status: 'Cue Slot Allocation',
      desc: 'Action-specific sound design cues aligned with individual shot action blueprints.',
    },
    {
      id: 'ambience',
      name: 'Environmental Room Tone & Ambience',
      icon: <Wind size={18} color="#22d3ee" />,
      status: 'Setting Context Mapped',
      desc: 'Atmospheric audio layer derived from scene setting descriptions.',
    },
  ];

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        padding: '20px',
      }}
      data-testid="audio-readiness-panel"
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
        <Volume2 size={20} color="#818cf8" />
        <div>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>
            Audio Production Readiness (Core V1 Architecture)
          </h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Provider-neutral audio stem schema and track layout ready for future audio rendering integration
          </p>
        </div>
      </div>

      {/* Auto-Ducking & Mix Spec Placeholder */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-default)',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.8125rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={16} color="#818cf8" />
          <span>
            <strong>Audio Pipeline Allocation:</strong> 4-stem layout (VO, BGM, SFX, Ambience) prepared for pluggable audio engine
          </span>
        </div>
        <span className="badge badge-draft" style={{ fontSize: '0.7rem' }}>
          Schema Ready
        </span>
      </div>

      {/* Audio Stems Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '16px',
        }}
      >
        {audioStems.map((stem) => (
          <div
            key={stem.id}
            className="card"
            style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {stem.icon}
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 600 }}>{stem.name}</h4>
              </div>
            </div>

            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              {stem.desc}
            </p>

            <div
              style={{
                marginTop: 'auto',
                paddingTop: '8px',
                borderTop: '1px solid var(--border-subtle)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '0.7rem',
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>Status:</span>
              <span className="badge badge-draft" style={{ fontSize: '0.65rem' }}>
                {stem.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
