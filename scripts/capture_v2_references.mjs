import {chromium} from '@playwright/test';import {spawn} from 'node:child_process';
const server=spawn('python',['-m','http.server','8794','--bind','127.0.0.1','--directory','build/v2'],{stdio:'ignore'});let browser;
try{for(let i=0;i<40;i++){try{await fetch('http://127.0.0.1:8794/');break;}catch{await new Promise(r=>setTimeout(r,100));}}
browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});const p=await browser.newPage();
await p.route('**/*',r=>r.request().url().startsWith('http://127.0.0.1:8794/')?r.continue():r.abort());
for(const [width,height] of [[1440,900],[1920,1080]]){
 await p.setViewportSize({width,height});await p.goto('http://127.0.0.1:8794/before/laya.html');await p.locator('.graph').waitFor();await p.waitForTimeout(250);await p.mouse.move(5,5);await p.screenshot({path:`build/v2/before/${width}-laya-overview.png`});
 await p.locator('.pane').first().getByRole('button',{name:'输出 act_logits',exact:true}).click();await p.screenshot({path:`build/v2/before/${width}-laya-selected.png`});
}
await p.setViewportSize({width:1400,height:1100});await p.goto('http://127.0.0.1:8794/');await p.setContent('<html><body style="margin:0;background:#171320;display:flex;align-items:center;justify-content:center;height:100vh"><img style="max-width:98vw;max-height:98vh" src="http://127.0.0.1:8794/reference/reference-sanitized.svg"></body></html>');await p.locator('img').evaluate(img=>img.decode());await p.screenshot({path:'build/v2/reference/full-reference-preview.png'});console.log('Before Laya and reference SVG previews captured');
}finally{await browser?.close();server.kill();}
