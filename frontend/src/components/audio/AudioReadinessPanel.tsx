import React from 'react';
import { Volume2, Mic, Music, Sparkles, Wind, Sliders } from 'lucide-react';

interface AudioReadinessPanelProps {
  projectId: string;
}

export const AudioReadinessPanel: React.FC<AudioReadinessPanelProps> = () => {
  const audioStems = [
    {
      id: 'vo',
      name: 'Voiceover (VO) / Narration',
      icon: <Mic size={18} color="#818cf8" />,
      status: 'Awaiting Script Approval',
      desc: 'Automatic ElevenLabs / OpenAI TTS voiceover track linked to scene narrations.',
    },
    {
      id: 'bgm',
      name: 'Background Music (BGM)',
      icon: <Music size={18} color="#fbbf24" />,
      status: 'Dynamic Beat Alignment Ready',
      desc: 'Adaptive cinematic soundtrack synced to shot duration cuts.',
    },
    {
      id: 'sfx',
      name: 'Sound Effects (SFX)',
      icon: <Sparkles size={18} color="#34d399" />,
      status: 'Cue Points Mapped',
      desc: 'Foley and action-synced sound cues based on shot action tags.',
    },
    {
      id: 'ambience',
      name: 'Environmental Ambience',
      icon: <Wind size={18} color="#22d3ee" />,
      status: 'Setting Context Active',
      desc: 'Continuous room tone and atmospheric presence derived from scene setting.',
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
            Pre-flight stems and ducking pipeline ready for audio rendering
          </p>
        </div>
      </div>

      {/* Auto-Ducking Mix Spec Banner */}
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
          <span><strong>Auto-Ducking Engine:</strong> BGM ducks -14dB when VO / Narration is active</span>
        </div>
        <span className="badge badge-approved" style={{ fontSize: '0.7rem' }}>
          Configured
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
                <h4 style={{ fontSize: '0.875rem', fontWeight: 600 }}>{stem.name}</h4>
              </div>
              <span className="badge badge-draft" style={{ fontSize: '0.65rem' }}>
                {stem.status}
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              {stem.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
