#!/usr/bin/env node
import {access, copyFile, mkdir, readFile, rm} from 'node:fs/promises';
import {basename, dirname, resolve} from 'node:path';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';

const args=Object.fromEntries(process.argv.slice(2).flatMap((v,i,a)=>v.startsWith('--')?[[v.slice(2),a[i+1]??true]]:[]));
const timeline=resolve(String(args.timeline??'')); const output=resolve(String(args.output??'renders/workout-edit.mp4')); const preflightOnly=Boolean(args['preflight-only']);
if(!args.timeline) throw new Error('Usage: npm run render -- --timeline <final-plan.json> [--output <video.mp4>]');
const plan=JSON.parse(await readFile(timeline,'utf8')); const allowed=new Set(['none','cut','hard_cut','motion_match','cross_dissolve','fade','dip_black','whip','glitch','push_cut','slide','wipe','zoom_blur']);
const errors=[]; const t=plan.timeline??{};
if(!Number.isFinite(t.fps)||t.fps<=0)errors.push('timeline: fps must be positive'); if(!Number.isFinite(t.duration_seconds)||t.duration_seconds<=0)errors.push('timeline: duration_seconds must be positive');
for(const s of t.segments??[]){const p=`segment ${s.segment_id??'<missing>'} at ${s.composition_start??'?'}s`;
 if(!s.source_path)errors.push(`${p}: missing source_path`); if(!(s.source_end>s.source_start))errors.push(`${p}: invalid source range`); if(s.composition_start<0||!(s.composition_duration>0))errors.push(`${p}: invalid composition range`); if(!allowed.has(s.transition_in?.type))errors.push(`${p}: unsupported transition ${s.transition_in?.type}`); if(!(s.playback_rate>0))errors.push(`${p}: invalid playback rate`);
 const points=s.time_remap?.keyframes??s.time_remap?.points??s.time_remap?.curve??[]; if(s.time_remap&&(!['dramatic_bell_curve','dramatic_slow_center','smooth','speed_curve',undefined].includes(s.time_remap.type)||points.length<2||points.some(x=>x.position<0||x.position>1||!((x.rate??x.speed)>0))))errors.push(`${p}: unsupported time-remap contract`);
}
const media=[...(t.segments??[]).map(s=>s.source_path),...(plan.soundtrack?[plan.soundtrack.src]:[])]; for(const p of media){try{await access(resolve(dirname(timeline),p));}catch{errors.push(`missing media: ${p}`)}}
if(errors.length)throw new Error(`Preflight failed:\n- ${errors.join('\n- ')}`); if(preflightOnly){console.log(`Preflight OK: ${media.length} media references`);process.exit(0)}
const publicDir=resolve('workout-remotion-editor/public/media'); await rm(publicDir,{recursive:true,force:true});await mkdir(publicDir,{recursive:true}); const names=new Set();
for(const p of media){const src=resolve(dirname(timeline),p), name=basename(p);if(names.has(name))throw new Error(`Preflight failed: media basename collision: ${name}`);names.add(name);await copyFile(src,resolve(publicDir,name));}
await mkdir(dirname(output),{recursive:true});
try{const serveUrl=await bundle({entryPoint:resolve('workout-remotion-editor/remotion/index.ts'),publicDir:resolve('workout-remotion-editor/public')});const composition=await selectComposition({serveUrl,id:'WorkoutEdit',inputProps:{plan}});await renderMedia({serveUrl,composition,codec:'h264',outputLocation:output,inputProps:{plan},pixelFormat:'yuv420p',crf:18});console.log(`Rendered ${output}`);}finally{await rm(publicDir,{recursive:true,force:true});}
