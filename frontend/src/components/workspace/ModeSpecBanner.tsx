import React from 'react';
import type { VideoMode } from '../../api/types';
import { Film, Sparkles, Repeat, Clapperboard, ChevronRight } from 'lucide-react';

interface ModeSpecBannerProps {
  mode: VideoMode;
}

export const ModeSpecBanner: React.FC<ModeSpecBannerProps> = ({ mode }) => {
  const getModeSpec = () => {
    switch (mode) {
      case 'STORY':
        return {
          steps: ['Story / Script Brief', 'Scene Acts & Headings', 'Storyboard Shots', 'Video Generation'],
          icon: <Film size={16} color="#818cf8" />,
          hint: 'Full narrative flow: Creative generator plans acts, scenes, and shots with continuity bibles.',
        };
      case 'SHORT':
        return {
          steps: ['Hook & Viral Concept', 'Fast Pacing Beat (Scene)', 'Punchy Shots', 'High-Impact Generation'],
          icon: <Sparkles size={16} color="#fbbf24" />,
          hint: 'Short mode: Optimized for immediate 3-second retention hooks and vertical 9:16 aspect ratio.',
        };
      case 'LOOP':
        return {
          steps: ['Loop Spec & Ambience', 'Seamless Scene', 'Matched Shot(s)', 'Continuous Render'],
          icon: <Repeat size={16} color="#34d399" />,
          hint: 'Loop mode: Maintains seamless start/end transitions for ambient, backgrounds, and motion graphics.',
        };
      case 'SCENE':
        return {
          steps: ['Single Scene Setting', 'Direct Shot Breakdown', 'Storyboard Grid', 'Shot Generation'],
          icon: <Clapperboard size={16} color="#22d3ee" />,
          hint: 'Scene mode: Rapid production of an isolated visual scene without needing full story scripts.',
        };
    }
  };

  const spec = getModeSpec();

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-panel)',
        borderRadius: '8px',
        padding: '12px 16px',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
      }}
      data-testid="mode-spec-banner"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {spec.icon}
        <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
          {spec.hint}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
        {spec.steps.map((step, idx) => (
          <React.Fragment key={step}>
            <span
              style={{
                color: idx === 2 ? 'var(--primary)' : 'var(--text-muted)',
                fontWeight: idx === 2 ? 600 : 400,
              }}
            >
              {step}
            </span>
            {idx < spec.steps.length - 1 && (
              <ChevronRight size={12} color="var(--border-default)" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
