import {test,expect} from '@playwright/test';
import fs from 'node:fs';

test('responsive evidence views, themes, fonts and refusal states',async({page})=>{
 const errors:string[]=[];
 page.on('pageerror',error=>errors.push(error.message));
 const observations:any[]=[];
 for(const width of [360,768,1280]){
  await page.setViewportSize({width,height:900});
  await page.goto('/hardcase/');
  for(const theme of ['light','dark']){
   if(await page.locator('html').getAttribute('data-theme')!==theme)await page.getByRole('button',{name:'Switch color theme'}).click();
   for(const [label,heading] of [['01 Search','A model earns its place here.'],['02 Training','What actually changed.'],['03 Evaluation','Improvement is a measurement.'],['04 Release','A candidate can be refused.'],['05 Data','Know what the model saw.']]){
    await page.getByRole('button',{name:label,exact:true}).click();
    await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible();
    const measured=await page.evaluate(async()=>{
     await document.fonts.ready;
     const cs=getComputedStyle(document.documentElement);
     const rgb=(hex:string)=>hex.trim().slice(1).match(/../g)!.map(s=>parseInt(s,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
     const luminance=(hex:string)=>rgb(hex).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
     const ratio=(a:string,b:string)=>{const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
     return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,headingFont:document.fonts.check('24px Fahkwang'),bodyFont:document.fonts.check('18px Varta'),monoFont:document.fonts.check('12px "M PLUS Code Latin"'),inkContrast:ratio(cs.getPropertyValue('--ink'),cs.getPropertyValue('--surface')),secondaryContrast:ratio(cs.getPropertyValue('--secondary'),cs.getPropertyValue('--surface')),controlContrast:ratio(cs.getPropertyValue('--control'),cs.getPropertyValue('--surface'))};
    });
    expect(measured.documentWidth).toBeLessThanOrEqual(width);
    expect(measured.headingFont&&measured.bodyFont&&measured.monoFont).toBeTruthy();
    expect(measured.inkContrast).toBeGreaterThanOrEqual(4.5);
    expect(measured.secondaryContrast).toBeGreaterThanOrEqual(4.5);
    expect(measured.controlContrast).toBeGreaterThanOrEqual(3);
    observations.push({width,theme,view:label,...measured});
   }
   await page.getByRole('button',{name:'01 Search',exact:true}).click();
   await page.screenshot({path:`../evidence/frontend/search-${width}-${theme}.png`,fullPage:true});
  }
 }
 await page.getByLabel('Scientific query').fill('A newly authored interface availability check.');
 await page.getByRole('button',{name:'Search papers',exact:true}).click();
 await expect(page.getByRole('status').first()).toContainText('No search was executed');
 await page.keyboard.press('Tab');
 expect(await page.evaluate(()=>document.activeElement?.tagName)).not.toBe('BODY');
 expect(errors).toEqual([]);
 fs.writeFileSync('../evidence/frontend/browser-checks.json',JSON.stringify({status:'passed',source_commit:process.env.GITHUB_SHA,run_id:process.env.GITHUB_RUN_ID,namespace:'interface_verification',live_inference:false,observations,errors}));
});
