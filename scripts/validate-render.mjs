#!/usr/bin/env node
import {spawnSync} from 'node:child_process';import {mkdir} from 'node:fs/promises';
const run=(cmd,args)=>{const r=spawnSync(cmd,args,{stdio:'inherit'});if(r.error)throw r.error;if(r.status)process.exit(r.status)};
run(process.execPath,['scripts/generate-fixtures.mjs']);run('npm',['run','build']);run(process.execPath,['scripts/render.mjs','--timeline','workout-remotion-editor/fixtures/generated/hybrid.json','--output','renders/phase18-smoke.mp4','--quality','preview']);await mkdir('renders/qa-frames',{recursive:true});run('ffmpeg',['-hide_banner','-loglevel','error','-y','-i','renders/phase18-smoke.mp4','-vf','select=eq(n\\,0)+eq(n\\,45)+eq(n\\,143)','-vsync','0','renders/qa-frames/frame-%02d.png']);
