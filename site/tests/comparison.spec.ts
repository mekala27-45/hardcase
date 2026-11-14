import {test,expect} from '@playwright/test';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {canonical,compareRankings,executeSuite,parseQueries,validateReceipt,type Receipt,type Request,type Snapshot,type Suite} from '../src/comparison';

const snapshot:Snapshot={base:{bundle_id:'base-bundle',generation:1},experimental:{bundle_id:'learned-bundle',generation:1}};
const hash=(query:string)=>createHash('sha256').update(query).digest('hex');
function receipt(alias:'base'|'experimental',query='authored fixture',depth=10):Receipt{
 const ids=Array.from({length:depth},(_,i)=>String(i));if(alias==='experimental'){ids.reverse();ids[depth-1]='outside';}
 return {id:alias+'-'+hash(query),alias,bundle_id:snapshot[alias].bundle_id,admission_generation:1,completion_generation:1,query_digest:hash(query),deployment_id:'fixture-deployment',corpus_digest:'same-corpus',graph_digest:alias+'-graph',tokenizer_digest:'tokenizer',index_digest:alias+'-index',status:'completed',fresh:true,replayed:false,top_document_ids:ids,results:ids.map(id=>({id,title:'Fixture document '+id,score:.5,visible_text:'Authored test fixture.'})),timings:{inference_ms:1}};
}
function fixtureRequest(override?:(path:string,options?:RequestInit)=>unknown){
 const calls:{path:string;body?:any}[]=[];const receipts=new Map<string,Receipt>();
 const request:Request=async(path,options)=>{
  const body=options?.body?JSON.parse(String(options.body)):undefined;calls.push({path,body});
  if(override){const value=override(path,options);if(value!==undefined)return value;}
  if(path==='/api/v1/models')return {aliases:Object.entries(snapshot).map(([name,row])=>({name,...row,available:true,valid:true}))};
  if(path==='/api/v1/sessions')return {capability:'fixture-only-do-not-publish-as-a-real-secret'};
  if(path==='/api/v1/search'){const r=receipt(body.alias,body.query,body.top_k);receipts.set(r.id,r);return r;}
  const r=receipts.get(decodeURIComponent(path.split('/').at(-1)!));
  if(!r)throw new Error('Unknown fixture path');
  // PostgreSQL JSONB may reorder keys. Structural equality must still pass.
  return Object.fromEntries(Object.entries(r).reverse());
 };
 return {request,calls};
}

test('rank diagnostics use explicit denominators and nullable missing ranks',()=>{
 const a=receipt('base'),b=receipt('experimental');const c=compareRankings(a,b);
 expect(c.shared).toBe(9);expect(c.jaccard).toBeCloseTo(9/11);
 expect(c.mean_shared_rank_shift).toBeCloseTo(41/9);
 expect(c.rows.find(r=>r.id==='0')?.learned_rank).toBeNull();
 expect(c.rows.find(r=>r.id==='outside')?.rank_change).toBeNull();
 const unchanged=compareRankings(a,{...a,id:'independent'});
 expect(unchanged.jaccard).toBe(1);expect(unchanged.mean_shared_rank_shift).toBe(0);
 const separate={...b,results:b.results.map(r=>({...r,id:'new-'+r.id}))};
 expect(compareRankings(a,separate).mean_shared_rank_shift).toBeNull();
});

test('identity, persistence, duplicate IDs and invalid inputs fail closed',()=>{
 const a=receipt('base');
 for(const change of [{query_digest:'changed'},{bundle_id:'changed'},{admission_generation:2},{completion_generation:2},{fresh:false},{replayed:true},{results:[a.results[0],...a.results.slice(0,9)]},{results:a.results.map(r=>({...r,score:NaN}))}])expect(()=>validateReceipt({...a,...change},'base',a.query_digest,10,snapshot)).toThrow();
 for(const change of [{query_digest:'different'},{corpus_digest:'different'},{deployment_id:'different'},{id:a.id}])expect(()=>compareRankings(a,{...receipt('experimental'),...change})).toThrow();
 expect(parseQueries(' first \r\n\n second ')).toEqual(['first','second']);
 for(const text of ['',Array(9).fill('x').join('\n'),'same\nsame','x'.repeat(513)])expect(()=>parseQueries(text)).toThrow();
 expect(parseQueries('🧬'.repeat(512))).toHaveLength(1);
});

test('suite captures aliases once, reads each receipt and omits raw inputs and credentials',async()=>{
 const {request,calls}=fixtureRequest();let concurrent=0,max=0;
 const serial:Request=async(...args)=>{max=Math.max(max,++concurrent);try{return await request(...args);}finally{concurrent--;}};
 const result=await executeSuite(['private input one','private input two'],10,serial,()=>{},()=>false,async()=>{});
 expect(result.status).toBe('completed');expect(result.rows).toHaveLength(2);expect(max).toBe(1);
 expect(calls.filter(r=>r.path==='/api/v1/search').map(r=>r.body.alias)).toEqual(['base','experimental','base','experimental']);
 expect(calls.filter(r=>r.path.startsWith('/api/v1/receipts/'))).toHaveLength(4);
 expect(canonical(result)).not.toContain('private input');expect(canonical(result)).not.toContain('capability');
 expect(result.quality_claim).toBe(false);
});

test('changed readback stops further requests and preserves failed denominator',async()=>{
 const {request,calls}=fixtureRequest(path=>path.startsWith('/api/v1/receipts/')?{wrong:'receipt'}:undefined);
 const result=await executeSuite(['query one','query two'],10,request,()=>{},()=>false,async()=>{});
 expect(result.status).toBe('incomplete');expect(result.planned).toBe(2);expect(result.rows.map(r=>r.status)).toEqual(['failed','not_run']);
 expect(result.rows[0].error).toContain('Persisted receipt differs');
 expect(calls.filter(r=>r.path==='/api/v1/search')).toHaveLength(1);
});

test('stop drains the current request and does not launch another',async()=>{
 const {request,calls}=fixtureRequest();let stopped=false;
 const result=await executeSuite(['query one','query two'],10,request,current=>{if(current.rows[0].receipts.base)stopped=true;},()=>stopped,async()=>{});
 expect(result.status).toBe('cancelled');expect(result.rows.every(r=>r.status==='cancelled')).toBe(true);
 expect(result.rows[0].receipts.base).toBeTruthy();expect(result.rows[0].comparison).toBeUndefined();
 expect(calls.filter(r=>r.path==='/api/v1/search')).toHaveLength(1);
});

test('interactive comparison, query navigation, report and mobile reflow',async({page})=>{
 const {request,calls}=fixtureRequest();const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/evidence.json',route=>route.fulfill({json:{api_url:'https://fixture.invalid',statement:'Scripted UI fixture, not model evidence.'}}));
 await page.route('https://fixture.invalid/**',async route=>{const req=route.request();const result=await request(new URL(req.url()).pathname,{method:req.method(),body:req.postData()});await route.fulfill({json:result});});
 await page.setViewportSize({width:390,height:900});await page.goto('/hardcase/#compare');
 await expect(page.getByRole('heading',{name:'See where models disagree.'})).toBeVisible();
 await page.getByLabel('Queries, one per line').fill('private input one\nprivate input two');
 await page.getByRole('button',{name:'Run comparison',exact:true}).click();
 await expect(page.locator('#comparison-status')).toContainText('Run completed. 2 of 2');
 await expect(page.getByRole('region',{name:'Paired ranking differences'})).toContainText('Outside list');
 await page.getByRole('button',{name:'Query 2: completed',exact:true}).click();
 await expect(page.locator('.comparison-detail h3')).toHaveText('Query 2');
 const saved=page.waitForEvent('download');await page.getByRole('button',{name:'Download diagnostic report'}).click();
 const file=await (await saved).path();const report:Suite=JSON.parse(fs.readFileSync(file!,'utf8'));
 expect(report.rows).toHaveLength(2);expect(JSON.stringify(report)).not.toContain('private input');expect(JSON.stringify(report)).not.toContain('Authorization');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await page.reload();await expect(page.getByLabel('Queries, one per line')).toBeEmpty();
 expect(calls.filter(r=>r.path==='/api/v1/search')).toHaveLength(4);expect(errors).toEqual([]);
});

test('UI retains a refused comparison without showing invented agreement',async({page})=>{
 const {request}=fixtureRequest(path=>path.startsWith('/api/v1/receipts/')?{wrong:true}:undefined);
 await page.route('**/evidence.json',route=>route.fulfill({json:{api_url:'https://fixture.invalid'}}));
 await page.route('https://fixture.invalid/**',async route=>{const r=route.request();await route.fulfill({json:await request(new URL(r.url()).pathname,{body:r.postData()})});});
 await page.goto('/hardcase/#compare');await page.getByRole('button',{name:'Load two example queries'}).click();
 await page.getByRole('button',{name:'Run comparison',exact:true}).click();
 await expect(page.locator('#comparison-status')).toContainText('Run incomplete. 0 of 2');
 await expect(page.locator('.comparison-error')).toContainText('Persisted receipt differs');
 await expect(page.locator('.comparison-metrics')).toHaveCount(0);
});
