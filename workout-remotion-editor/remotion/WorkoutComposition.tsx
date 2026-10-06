import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, OffthreadVideo, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {RepCounter, RepCounterEvent} from './RepCounter';
import {cropAtFrame, NormalizedTimelinePlan, secondsToFrame, sourceTimeAtFrame, TimelineSegment} from './timelineAdapter';

export type RenderProps = {plan: NormalizedTimelinePlan};
const media = (path: string) => `/media/${encodeURIComponent(path.replaceAll('\\','/').split('/').pop() ?? path)}`;

const transitionStyle = (s: TimelineSegment, frame: number, fps: number): React.CSSProperties => {
  const n=Math.max(0,secondsToFrame(s.transition_in.duration_seconds,fps)); if (!n || frame>=n) return {};
  const p=interpolate(frame,[0,n],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.inOut(Easing.ease)});
  switch(s.transition_in.type) {
    case 'fade': case 'cross_dissolve': case 'motion_match': return {opacity:p};
    case 'dip_black': return {opacity:p};
    case 'push_cut': case 'slide': return {transform:`translateX(${(1-p)*100}%)`};
    case 'wipe': return {clipPath:`inset(0 ${(1-p)*100}% 0 0)`};
    case 'zoom_blur': return {opacity:p,filter:`blur(${(1-p)*16}px)`,transform:`scale(${1.12-p*.12})`};
    case 'whip': return {transform:`translateX(${(1-p)*35}%)`,filter:`blur(${(1-p)*10}px)`};
    default:return {};
  }
};
const Glitch: React.FC<{progress:number}> = ({progress}) => <AbsoluteFill style={{pointerEvents:'none',opacity:1-progress}}>{[0,1,2,3,4,5].map(i=><div key={i} style={{position:'absolute',top:0,bottom:0,left:`${i*18}%`,width:'12%',background:i%2?'rgba(255,0,95,.20)':'rgba(0,255,255,.20)',transform:`translateX(${(i%2?1:-1)*(1-progress)*38}px)`,mixBlendMode:'screen'}}/>)}</AbsoluteFill>;
const Clip: React.FC<{segment:TimelineSegment; sourceAudioMuted:boolean}> = ({segment,sourceAudioMuted}) => {
  const frame=useCurrentFrame(), {fps}=useVideoConfig(); const duration=Math.max(1,secondsToFrame(segment.composition_duration,fps));
  const sourceFrame=secondsToFrame(sourceTimeAtFrame(segment,frame,fps),fps); const crop=cropAtFrame(segment.crop??segment.reframe,frame,duration);
  const fit=(segment.crop??segment.reframe)?.fit ?? 'cover'; const tr=transitionStyle(segment,frame,fps); const glitch=segment.transition_in.type==='glitch'&&frame<secondsToFrame(segment.transition_in.duration_seconds,fps);
  return <AbsoluteFill style={{overflow:'hidden',backgroundColor:'#000',...tr}}>
    <OffthreadVideo src={media(segment.source_path)} trimBefore={Math.max(0,sourceFrame-frame)} volume={sourceAudioMuted?0:1} style={{width:'100%',height:'100%',objectFit:fit,objectPosition:`${crop.x}% ${crop.y}%`,transform:`scale(${crop.scale})`}}/>
    {glitch?<Glitch progress={frame/Math.max(1,secondsToFrame(segment.transition_in.duration_seconds,fps))}/>:null}
    {(segment.text_overlays??[]).map((o,i)=>frame>=secondsToFrame(o.start_seconds,fps)&&frame<secondsToFrame(o.end_seconds,fps)?<div key={o.id??i} style={{position:'absolute',left:'7%',right:'7%',textAlign:'center',top:o.position==='top'?'8%':o.position==='center'?'46%':undefined,bottom:!o.position||o.position==='bottom'?'12%':undefined,color:'white',font:'700 48px Arial',textShadow:'0 3px 12px #000'}}>{o.text}</div>:null)}
  </AbsoluteFill>;
};
const Soundtrack: React.FC<{plan:NormalizedTimelinePlan}> = ({plan}) => {const frame=useCurrentFrame(),{fps,durationInFrames}=useVideoConfig(),s=plan.soundtrack;if(!s)return null;const start=secondsToFrame(s.offset_seconds,fps), fadeIn=secondsToFrame(s.fade_in_seconds,fps),fadeOut=secondsToFrame(s.fade_out_seconds,fps);const local=frame-start;let volume=s.volume;if(fadeIn)volume*=interpolate(local,[0,fadeIn],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});if(fadeOut)volume*=interpolate(frame,[durationInFrames-fadeOut,durationInFrames],[1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});return <Sequence from={start}><Audio src={media(s.src)} trimBefore={secondsToFrame(s.trim_start_seconds,fps)} durationInFrames={s.trim_end_seconds>s.trim_start_seconds?secondsToFrame(s.trim_end_seconds-s.trim_start_seconds,fps):undefined} volume={volume} loop={s.loop||s.shortfall_policy==='loop'}/></Sequence>};
export const WorkoutComposition:React.FC<RenderProps>=({plan})=>{const {fps}=useVideoConfig();const events:RepCounterEvent[]=plan.timeline.segments.flatMap(s=>s.replay_type==='hook_replay'||!s.rep_counter_eligible?[]:(s.counter_events??[]).map((e,i)=>({id:`${s.segment_id}-${e.rep_id}`,editorial_repetition_id:e.rep_id,source_id:s.source_path,segment_id:s.segment_id,composition_time:e.composition_time,frame:secondsToFrame(e.composition_time,fps),displayed_count:e.display_number,target:e.target,display_mode:e.display_mode??'number',stream_id:'workout',scope_start_frame:0})));return <AbsoluteFill style={{background:'#000'}}>{plan.timeline.segments.map(s=><Sequence key={s.segment_id} name={s.segment_id} from={secondsToFrame(s.composition_start,fps)} durationInFrames={Math.max(1,secondsToFrame(s.composition_duration,fps))}><Clip segment={s} sourceAudioMuted={plan.source_audio!=='preserve'}/></Sequence>)}<Soundtrack plan={plan}/><RepCounter events={events}/></AbsoluteFill>};
