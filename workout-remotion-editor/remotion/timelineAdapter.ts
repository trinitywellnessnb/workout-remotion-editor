/** Renderer-only adapter for Phase 12 normalized timelines.
 *
 * Shot choice, ordering, style, repetitions, and timing are intentionally
 * absent from this module: the Python composer owns those decisions.
 */
export type TimelineSegment = {
  segment_id: string;
  source_path: string;
  source_start: number;
  source_end: number;
  composition_start: number;
  composition_duration: number;
  playback_rate: number;
  time_remap: unknown | null;
  transition_in: {type: string; duration_seconds: number; model: "cut" | "overlap"};
  overlay_regions: string[];
  rep_counter_eligible: boolean;
  rep_ids: string[];
  display_rep_numbers: number[];
};

export type NormalizedTimelinePlan = {
  source_audio: "muted" | "preserve";
  timeline: {fps: number; duration_seconds: number; aspect_ratio: string; segments: TimelineSegment[]};
};

export const timelineToRemotionProps = (plan: NormalizedTimelinePlan) => {
  const {fps, duration_seconds: duration, aspect_ratio: aspectRatio, segments} = plan.timeline;
  return {
    fps,
    durationInFrames: Math.ceil(duration * fps),
    aspectRatio,
    sourceAudioMuted: plan.source_audio !== "preserve",
    clips: segments.map((segment) => ({
      id: segment.segment_id,
      src: segment.source_path,
      sourceStartFrame: Math.round(segment.source_start * fps),
      sourceEndFrame: Math.round(segment.source_end * fps),
      from: Math.round(segment.composition_start * fps),
      durationInFrames: Math.max(1, Math.round(segment.composition_duration * fps)),
      playbackRate: segment.playback_rate,
      timeRemap: segment.time_remap,
      transitionIn: segment.transition_in,
      overlays: {
        safeRegions: segment.overlay_regions,
        repCounter: {
          enabled: segment.rep_counter_eligible,
          repIds: segment.rep_ids,
          displayNumbers: segment.display_rep_numbers,
        },
      },
    })),
  };
};
