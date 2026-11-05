import {test,expect} from '@playwright/test';
import fs from 'node:fs';

test('scripted populated evidence controls and 200 percent reflow',async({page})=>{
 page.setDefaultTimeout(10000);
 const fixtures={
  completion_state:'Interface fixture, not experiment evidence',
  statement:'Scripted interface test. These values are not model observations.',
  training:{arms:[{arm:'uniform_contrastive',status:'fixture',updates:2,selected_update:1}],steps:[
   {arm:'uniform_contrastive',update:1,loss:1,contrastive_loss:1,distillation_loss:0,gradient_norm:.5,update_norm:.1,learning_rate:.01,cumulative_examples:8,encoded_tokens:100,elapsed_seconds:1,samples:[{query_id:'fixture-q',positive_id:'fixture-positive',candidate_ids:['fixture-positive','fixture-unjudged'],candidate_digest:'fixture-digest'}]},
   {arm:'uniform_contrastive',update:2,loss:.5,contrastive_loss:.5,distillation_loss:0,gradient_norm:.3,update_norm:.1,learning_rate:.01,cumulative_examples:16,encoded_tokens:100,elapsed_seconds:1,samples:[]}
  ],parameters:[{arm:'uniform_contrastive',parameter:'fixture.block',trainable:true,changed:true,before_digest:'a',after_digest:'b'}]},
  evaluation:{status:'scripted fixture',methods:[{method:'base_encoder',status:'completed',ndcg10:.5,recall10:.5,recall100:1,mrr10:.5,completed_queries:2,planned_queries:2},{method:'uniform_contrastive',status:'completed',ndcg10:.6,recall10:.5,recall100:1,mrr10:.5,completed_queries:2,planned_queries:2}],paired_rows:[{query_id:'fixture-A',query:'Authored alpha fixture',category:'gain',base_ndcg10:.4,candidate_ndcg10:.6,difference:.2},{query_id:'fixture-B',query:'Authored beta fixture',category:'loss',base_ndcg10:.6,candidate_ndcg10:.4,difference:-.2}],slices:{summaries:[{slice:'length_bin',value:'fixture-short',method:'base_encoder',planned_queries:2,completed_queries:2,mean_ndcg10:.5},{slice:'lexical_overlap_bin',value:'fixture-overlap',method:'base_encoder',planned_queries:2,completed_queries:2,mean_ndcg10:.5}]}},
  data:{inventory:[],audit:[]},release:{}
 };
 await page.route('**/evidence.json',route=>route.fulfill({json:fixtures}));
 const observations:any[]=[];
 for(const width of [360,768,1440]){
  await page.setViewportSize({width,height:1000});
  await page.goto('/hardcase/');
  for(const theme of ['light','dark']){
   if(await page.locator('html').getAttribute('data-theme')!==theme)await page.getByRole('button',{name:'Switch color theme'}).click();
   await page.getByRole('button',{name:'02 Training',exact:true}).click();
   await page.getByRole('button',{name:'Inspect evidence',exact:true}).first().click();
   await page.getByLabel('Recorded update').selectOption('1');
   await expect(page.locator('#update-detail')).toContainText('fixture-positive');
   await page.getByText('Parameter-change evidence',{exact:true}).click();
   await expect(page.locator('#training-ledger')).toContainText('fixture.block');
   await page.getByRole('button',{name:'03 Evaluation',exact:true}).click();
   await page.getByLabel('Find a query or ID').fill('alpha');
   await expect(page.locator('#paired-table')).toContainText('fixture-A');
   await expect(page.locator('#paired-table')).not.toContainText('fixture-B');
   await page.getByLabel('Slice',{exact:true}).selectOption('lexical_overlap_bin');
   await expect(page.locator('#slice-table')).toContainText('fixture-overlap');
   const widths=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth,chartMinimum:Math.min(...Array.from(document.querySelectorAll('.chart-scroll svg')).map(n=>n.getBoundingClientRect().width))}));
   expect(widths.document).toBeLessThanOrEqual(width);
   expect(widths.chartMinimum).toBeGreaterThanOrEqual(680);
   observations.push({width,theme,...widths});
  }
 }
 await page.setViewportSize({width:1440,height:1000});
 await page.evaluate(()=>document.documentElement.style.zoom='2');
 const reflow=await page.evaluate(()=>({zoom:getComputedStyle(document.documentElement).zoom,right:document.querySelector('main')!.getBoundingClientRect().right,viewport:innerWidth}));
 expect(reflow.right).toBeLessThanOrEqual(reflow.viewport+1);
 await page.emulateMedia({reducedMotion:'reduce'});
 expect(await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches)).toBeTruthy();
 fs.writeFileSync('../evidence/frontend/scripted-controls.json',JSON.stringify({namespace:'scripted_interface',model_execution:false,status:'passed',source_commit:process.env.GITHUB_SHA,observations,reflow,zoom_mode:'CSS 200 percent reflow, not native browser zoom control'}));
});
