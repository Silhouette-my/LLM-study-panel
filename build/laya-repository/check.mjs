import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import {writeFileSync} from 'node:fs';
const server=spawn('python',['-m','http.server','8790','--bind','127.0.0.1','--directory','build'],{stdio:'ignore'});
let browser;
try {
 for(let i=0;i<40;i++) {
  try {await fetch('http://127.0.0.1:8790/');break;} catch {await new Promise(r=>setTimeout(r,100));}
 }
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 const results=[];
 for(const name of ['decision','attention']) {
  const page=await browser.newPage({viewport:{width:1366,height:768}});
  const errors=[],network=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('request',r=>{if(/^https?:/.test(r.url())&&r.resourceType()!=='document')network.push(r.url());});
  await page.goto(`http://127.0.0.1:8790/laya-repository/${name}.html`);
  await page.getByTestId('coverage-warning').waitFor();
  if(name==='attention') {
   await page.getByRole('button',{name:'计算细节',exact:true}).click();
   await page.locator('.accessible-nodes button').filter({hasText:'F.scaled_dot_product_attention'}).click();
   await page.getByRole('button',{name:'源码',exact:true}).click();
   const source=await page.getByTestId('source').textContent();
   if(!source.includes('F.scaled_dot_product_attention'))throw Error('Attention source mapping lost');
  } else {
   await page.locator('.accessible-nodes').getByRole('button',{name:'输出 logits',exact:true}).waitFor();
   await page.locator('.accessible-nodes').getByRole('button',{name:'输出 act_logits',exact:true}).waitFor();
  }
  await page.screenshot({path:`build/laya-repository/${name}-preview.png`});
  if(errors.length||network.length)throw Error(JSON.stringify({name,errors,network}));
  results.push({name,status:'passed',transport:'local HTTP',errors,additionalRequests:network});
  await page.close();
 }
 writeFileSync('build/laya-repository/browser-results.json',JSON.stringify(results,null,2));
 console.log(JSON.stringify(results));
}finally {await browser?.close();server.kill();}
