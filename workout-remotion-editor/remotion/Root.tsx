import React from 'react';
import {Composition} from 'remotion';
import fixture from './default-plan.json';
import {WorkoutComposition, RenderProps} from './WorkoutComposition';
import {timelineToRemotionProps, NormalizedTimelinePlan} from './timelineAdapter';
const defaults={plan:fixture as NormalizedTimelinePlan};
export const RemotionRoot:React.FC=()=> <Composition<RenderProps> id="WorkoutEdit" component={WorkoutComposition} width={1080} height={1920} fps={30} durationInFrames={30} defaultProps={defaults} calculateMetadata={({props})=>{const m=timelineToRemotionProps(props.plan);return {durationInFrames:m.durationInFrames,fps:m.fps,width:m.width,height:m.height,props};}}/>;
