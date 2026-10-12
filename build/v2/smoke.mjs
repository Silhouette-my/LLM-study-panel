import {chromium} from '@playwright/test';import {spawn} from 'node:child_process';import {writeFileSync} from 'node:fs';
const s=spawn('python',['-m','http.server','8793','--bind','127.0.0.1','--directory','build'],{stdio:'ignore'});let b;
try{for(let i=0;i<40;i++){try{await fetch('http://127.0.0.1:8793/');break;}catch{await new Promise(r=>setTimeout(r,100));}}
b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});const p=await b.newPage({viewport:{width:1440,height:900}}),errors=[];p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
for(const [name,path] of [['mha','mha.html'],['laya','laya-repository/decision.html'],['compare','model_atlas_demo.html']]){await p.goto('http://127.0.0.1:8793/'+path);await p.locator('.graph[data-layout-ready=true]').first().waitFor({timeout:15000});await p.waitForTimeout(200);await p.screenshot({path:`build/v2/after/smoke-${name}.png`});console.log(name,await p.evaluate(()=>window.__atlasMetrics));}
writeFileSync('build/v2/after/smoke-errors.json',JSON.stringify(errors));console.log('errors',errors);
}finally{await b?.close();s.kill();}
