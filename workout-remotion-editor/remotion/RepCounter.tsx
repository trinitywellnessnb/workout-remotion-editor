import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export type RepCounterEvent = {
  id: string;
  editorial_repetition_id: string;
  source_id: string;
  segment_id?: string | null;
  composition_time: number;
  frame: number;
  displayed_count: number;
  source_rep_number?: number | null;
  side?: 'left' | 'right' | null;
  target?: number | null;
  display_mode: 'number' | 'rep' | 'progress';
  stream_id: string;
  scope_start_frame: number;
};

export type RepCounterProps = {
  events: RepCounterEvent[];
  placement?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  animationEnabled?: boolean;
};

const placementStyle = (placement: NonNullable<RepCounterProps['placement']>): React.CSSProperties => ({
  position: 'absolute',
  top: placement.startsWith('top') ? '7%' : undefined,
  bottom: placement.startsWith('bottom') ? '12%' : undefined,
  left: placement.endsWith('left') ? '6%' : undefined,
  right: placement.endsWith('right') ? '6%' : undefined,
});

/** Pure presentation: all editorial decisions and source-time mapping happen upstream. */
export const RepCounter: React.FC<RepCounterProps> = ({
  events,
  placement = 'top-right',
  animationEnabled = true,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const activeStream = [...events]
    .filter((event) => event.scope_start_frame <= frame)
    .sort((a, b) => b.scope_start_frame - a.scope_start_frame)[0]?.stream_id;
  const current = [...events].reverse().find(
    (event) => event.stream_id === activeStream && event.frame <= frame,
  );
  if (!current) return null;
  if (current.display_mode === 'progress' && !current.target) return null;
  const age = frame - current.frame;
  const pop = animationEnabled && age < Math.round(fps * 0.28)
    ? spring({frame: age, fps, config: {damping: 14, stiffness: 220, mass: 0.55}})
    : 1;
  const scale = interpolate(pop, [0, 1], [0.86, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const label = current.display_mode === 'number'
    ? `${current.displayed_count}`
    : current.display_mode === 'rep'
      ? `REP ${current.displayed_count}`
      : `${current.displayed_count} / ${current.target}`;
  return <div aria-label="Reviewed repetition count" style={{
    ...placementStyle(placement),
    transform: `scale(${scale})`,
    transformOrigin: placement.endsWith('right') ? 'right center' : 'left center',
    padding: '12px 18px',
    borderRadius: 18,
    background: 'rgba(8, 12, 18, 0.82)',
    border: '2px solid rgba(255,255,255,0.9)',
    boxShadow: '0 4px 18px rgba(0,0,0,0.4)',
    color: '#fff',
    fontFamily: 'Inter, Arial, sans-serif',
    fontWeight: 800,
    fontSize: 54,
    lineHeight: 1,
    fontVariantNumeric: 'tabular-nums',
  }}>{label}</div>;
};
