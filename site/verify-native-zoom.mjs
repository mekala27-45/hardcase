import {chromium} from '@playwright/test';
import {spawn,execFileSync} from 'node:child_process';
import {mkdirSync,writeFileSync} from 'node:fs';
const directory='../evidence/frontend';
mkdirSync(directory,{recursive:true});
const preview=spawn(process.execPath,['node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','4173'],{stdio:'ignore'});
const native=(...args)=>execFileSync('xdotool',args,{encoding:'utf8',timeout:10000});
let browser;
const record={namespace:'interface_accessibility',model_execution:false,source_commit:process.env.GITHUB_SHA,zoom_method:'Native Chromium page zoom using X11 keyboard events',observations:[]};
try {
  let ready=false;
  for(let i=0;i<60;i++){try{ready=(await fetch('http://127.0.0.1:4173/hardcase/')).ok;}catch{}if(ready)break;await new Promise(r=>setTimeout(r,100));}
  if(!ready)throw new Error('Preview did not start');
  browser=await chromium.launch({headless:false,args:['--window-size=1440,1000']});
  const context=await browser.newContext({viewport:null});
  const page=await context.newPage();
  await page.goto('http://127.0.0.1:4173/hardcase/');
  await page.locator('#theme').waitFor();
  await page.evaluate(()=>{document.title='Hardcase native zoom verification';});
  await page.waitForTimeout(200);
  const window=native('search','--onlyvisible','--name','Hardcase native zoom verification').trim().split(/\s+/).at(-1);
  if(!window)throw new Error('Chromium window not found');
  native('windowfocus','--sync',window);
  native('key','--clearmodifiers','ctrl+0');
  await page.waitForTimeout(150);
  record.before=await page.evaluate(()=>({dpr:devicePixelRatio,viewport:innerWidth,outer:outerWidth}));
  for(let i=0;i<5;i++){native('key','--clearmodifiers','ctrl+plus');await page.waitForTimeout(100);}
  await page.waitForFunction(()=>devicePixelRatio>=1.99,null,{timeout:5000});
  record.after=await page.evaluate(()=>({dpr:devicePixelRatio,viewport:innerWidth,outer:outerWidth}));
  if(Math.abs(record.after.dpr/record.before.dpr-2)>.02||Math.abs(record.before.viewport/record.after.viewport-2)>.05)throw new Error('Native 200-percent zoom was not established: '+JSON.stringify(record.after));
  for(const theme of ['light','dark']){
    if(await page.evaluate(()=>document.documentElement.dataset.theme)!==theme)await page.locator('#theme').click();
    for(const view of ['search','training','evaluation','release','data']){
      await page.locator('[data-panel="'+view+'"]').click();
      await page.waitForFunction(view=>document.querySelector('[data-panel="'+view+'"]').getAttribute('aria-current')==='page',view);
      await page.evaluate(()=>document.fonts.ready);
      const dimensions=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth,dpr:devicePixelRatio,font:getComputedStyle(document.body).fontFamily}));
      if(dimensions.document>dimensions.viewport+1)throw new Error('Page overflow at native zoom: '+theme+'/'+view);
      record.observations.push({theme,view,...dimensions});
    }
    await page.screenshot({path:directory+'/native-zoom-200-'+theme+'.png',fullPage:true});
  }
  record.status='passed';
}catch(error){record.status='failed';record.error=String(error);throw error;}
finally{record.observed_at=new Date().toISOString();writeFileSync(directory+'/native-zoom.json',JSON.stringify(record,null,2)+'\n');await browser?.close();preview.kill('SIGTERM');}
