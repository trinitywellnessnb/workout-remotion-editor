/** Deterministic, renderer-only adapter for the Phase 12 normalized contract. */
export const SUPPORTED_TRANSITIONS = ['none', 'cut', 'hard_cut', 'motion_match', 'cross_dissolve', 'fade', 'dip_black', 'whip', 'glitch', 'push_cut', 'slide', 'wipe', 'zoom_blur'] as const;
export type TransitionType = typeof SUPPORTED_TRANSITIONS[number];
export type Point = {position: number; rate?: number; speed?: number; x?: number; y?: number; scale?: number};
export type Crop = {fit?: 'cover'|'contain'|'fill'; x?: number; y?: number; scale?: number; keyframes?: Point[]};
export type TextOverlay = {id?: string; text: string; start_seconds: number; end_seconds: number; kind?: 'title'|'exercise'|'tip'|'caption'; position?: 'top'|'bottom'|'center'};
export type CounterEvent = {rep_id: string; display_number: number; composition_time: number; target?: number; display_mode?: 'number'|'rep'|'progress'};
export type TimelineSegment = {
  segment_id: string; source_path: string; source_start: number; source_end: number;
  composition_start: number; composition_end?: number; composition_duration: number;
  playback_rate: number; time_remap: null | {type?: string; curve_type?: string; keyframes?: Point[]; points?: Point[]; curve?: Point[]};
  transition_in: {type: TransitionType; duration_seconds: number; model: 'cut'|'overlap'};
  overlay_regions?: string[]; text_overlays?: TextOverlay[]; crop?: Crop; reframe?: Crop;
  rep_counter_eligible?: boolean; replay_type?: string|null; rep_ids?: string[]; display_rep_numbers?: number[]; counter_events?: CounterEvent[];
};
export type Soundtrack = {src: string; offset_seconds: number; trim_start_seconds: number; trim_end_seconds: number; volume: number; fade_in_seconds: number; fade_out_seconds: number; loop: boolean; shortfall_policy: 'leave_silence'|'loop'};
export type NormalizedTimelinePlan = {source_audio: 'muted'|'preserve'; soundtrack?: Soundtrack|null; timeline: {fps: number; duration_seconds: number; aspect_ratio: string; width?: number; height?: number; segments: TimelineSegment[]}};
export const secondsToFrame = (seconds: number, fps: number) => Math.round(seconds * fps);
const points = (s: TimelineSegment) => s.time_remap?.keyframes ?? s.time_remap?.points ?? s.time_remap?.curve ?? [];
const speedAt = (p: Point[], position: number, fallback: number) => {
  if (!p.length) return fallback;
  if (position <= p[0].position) return p[0].rate ?? p[0].speed ?? fallback;
  const rightIndex = p.findIndex((x) => x.position >= position);
  if (rightIndex < 0) return p[p.length - 1].rate ?? p[p.length - 1].speed ?? fallback;
  const a = p[rightIndex - 1], b = p[rightIndex];
  const t = (position - a.position) / Math.max(1e-9, b.position - a.position);
  return (a.rate ?? a.speed ?? fallback) + ((b.rate ?? b.speed ?? fallback) - (a.rate ?? a.speed ?? fallback)) * t;
};
/** Inverts the composer's integral of reciprocal speed over source position.
 * The lookup is absolute (not stateful), so parallel frame rendering cannot drift.
 */
export const sourceTimeAtFrame = (s: TimelineSegment, localFrame: number, fps: number) => {
  if (!s.time_remap) return Math.min(s.source_end, s.source_start + localFrame / fps * s.playback_rate);
  const p = points(s), sourceDuration=s.source_end-s.source_start, steps=2048;
  const target=Math.min(1,Math.max(0,(localFrame/fps)/s.composition_duration));
  const cumulative=[0]; let total=0;
  for(let i=1;i<=steps;i++){const a=(i-1)/steps,b=i/steps;total+=(b-a)*(.5/speedAt(p,a,s.playback_rate)+.5/speedAt(p,b,s.playback_rate));cumulative.push(total);}
  const wanted=target*total; let lo=0,hi=steps;
  while(lo<hi){const mid=(lo+hi)>>1;if(cumulative[mid]<wanted)lo=mid+1;else hi=mid;}
  const i=Math.max(1,lo), span=cumulative[i]-cumulative[i-1], fraction=span?((wanted-cumulative[i-1])/span):0;
  const sourcePosition=((i-1)+fraction)/steps;
  return Math.min(s.source_end,s.source_start+sourcePosition*sourceDuration);
};
export const cropAtFrame = (crop: Crop|undefined, frame: number, duration: number): Required<Pick<Crop,'x'|'y'|'scale'>> => {
  const fallback = {x: crop?.x ?? 50, y: crop?.y ?? 50, scale: crop?.scale ?? 1}; const p = crop?.keyframes ?? [];
  if (!p.length) return fallback;
  const pos = duration <= 1 ? 1 : frame / (duration - 1); const ri = p.findIndex(k => k.position >= pos);
  if (ri <= 0) return {x:p[0].x ?? fallback.x,y:p[0].y ?? fallback.y,scale:p[0].scale ?? fallback.scale};
  if (ri < 0) {const z=p[p.length-1]; return {x:z.x??fallback.x,y:z.y??fallback.y,scale:z.scale??fallback.scale};}
  const a=p[ri-1],b=p[ri], raw=(pos-a.position)/Math.max(1e-9,b.position-a.position); const t=raw*raw*(3-2*raw);
  return {x:(a.x??fallback.x)+((b.x??fallback.x)-(a.x??fallback.x))*t,y:(a.y??fallback.y)+((b.y??fallback.y)-(a.y??fallback.y))*t,scale:(a.scale??fallback.scale)+((b.scale??fallback.scale)-(a.scale??fallback.scale))*t};
};
export const timelineToRemotionProps = (plan: NormalizedTimelinePlan) => {
  const {fps, duration_seconds, aspect_ratio, width=1080, height=1920, segments} = plan.timeline;
  return {plan, fps, width, height, durationInFrames: Math.max(1, Math.ceil(duration_seconds*fps)), aspectRatio: aspect_ratio, sourceAudioMuted: plan.source_audio !== 'preserve', clips: segments.map(s => ({...s, from: secondsToFrame(s.composition_start,fps), durationInFrames: Math.max(1,secondsToFrame(s.composition_duration,fps))}))};
};
