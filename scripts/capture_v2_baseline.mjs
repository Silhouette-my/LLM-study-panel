import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import {writeFileSync} from 'node:fs';
const server=spawn('python',['-m','http.server','8792','--bind','127.0.0.1','--directory','build/v2/before'],{stdio:'ignore'});
let browser;
try{
 for(let i=0;i<40;i++){try{await fetch('http://127.0.0.1:8792/');break;}catch{await new Promise(r=>setTimeout(r,100));}}
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 const results=[];
 for(const [width,height] of [[1440,900],[1920,1080]]){
  const page=await browser.newPage({viewport:{width,height}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8792/mha.html');
  await page.locator('.graph').waitFor();
  await page.waitForFunction(()=>document.querySelector('.graph')?._cyreg?.cy.nodes().first().position().y>0);
  await page.screenshot({path:`build/v2/before/${width}-overview.png`});
  await page.locator('.pane').first().getByRole('button',{name:'blocks.0',exact:true}).click();
  await page.screenshot({path:`build/v2/before/${width}-selected.png`});
  await page.getByRole('button',{name:'进入模块',exact:true}).click();
  await page.locator('.pane').first().getByRole('button',{name:'attention',exact:true}).waitFor();
  await page.screenshot({path:`build/v2/before/${width}-entered.png`});
  await page.goto('http://127.0.0.1:8792/laya.html');
  await page.getByTestId('coverage-warning').waitFor();
  await page.locator('.coverage-warning summary').click();
  await page.locator('.analysis-details summary').click();
  await page.screenshot({path:`build/v2/before/${width}-diagnostics.png`});
  await page.goto('http://127.0.0.1:8792/model_atlas_demo.html');
  await page.locator('.pane').first().getByRole('button',{name:'blocks.0',exact:true}).waitFor();
  await page.screenshot({path:`build/v2/before/${width}-comparison.png`});
  results.push({width,height,errors,browser:browser.version(),hardware:await page.evaluate(()=>({cores:navigator.hardwareConcurrency,memory:navigator.deviceMemory??null}))});
  await page.close();
 }
 writeFileSync('build/v2/before/screenshots.json',JSON.stringify(results,null,2));
 console.log(JSON.stringify(results));
}finally{await browser?.close();server.kill();}
