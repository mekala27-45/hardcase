/** Diagnostic comparisons of live lists, separate from the frozen quality study. */
export type Alias = 'base' | 'experimental';
export type Document = {id:string; title:string; score:number; visible_text:string};
export type Receipt = {
 id:string; alias:Alias; status:string; fresh:boolean; replayed:boolean;
 bundle_id:string; admission_generation:number; completion_generation:number;
 query_digest:string; deployment_id:string; corpus_digest:string;
 graph_digest:string; tokenizer_digest:string; index_digest:string;
 top_document_ids:string[]; results:Document[]; timings:Record<string,number|string>;
};
export type Snapshot = Record<Alias,{bundle_id:string;generation:number}>;
export type RankedDocument = {id:string;title:string;base_rank:number|null;learned_rank:number|null;rank_change:number|null;rrf_score:number};
export type Pair = {
 index:number;query_digest:string;status:'pending'|'running'|'completed'|'failed'|'cancelled'|'not_run';error?:string;
 receipts:Partial<Record<Alias,Receipt>>;milliseconds:Partial<Record<Alias,number>>;
 comparison?:ReturnType<typeof compareRankings>;
};
export type Suite = {schema_version:1;namespace:'live_ranking_diagnostics';quality_claim:false;started_at:string;ended_at?:string;depth:number;planned:number;status:'running'|'completed'|'incomplete'|'cancelled';snapshot?:Snapshot;rows:Pair[]};
export type Request = (path:string,options?:RequestInit)=>Promise<any>;
function ensure(ok:unknown,message:string):asserts ok {if(!ok)throw new Error(message);}
const order = (a:string,b:string)=>a<b?-1:a>b?1:0;

export function parseQueries(text:string):string[]{
 const queries=text.split(/\r?\n/).map(q=>q.trim()).filter(Boolean);
 ensure(queries.length>=1&&queries.length<=8,'Enter one to eight queries, one per line.');
 ensure(queries.every(q=>[...q].length<=512),'Each query must contain at most 512 characters.');
 ensure(new Set(queries).size===queries.length,'Remove duplicate queries before running the suite.');
 return queries;
}
export async function queryDigest(query:string){
 return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(query))),b=>b.toString(16).padStart(2,'0')).join('');
}
export function canonical(value:any):string{
 if(value===null||typeof value!=='object')return JSON.stringify(value);
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
}
export function validateReceipt(receipt:Receipt,alias:Alias,query:string,depth:number,snapshot:Snapshot){
 ensure(receipt?.status==='completed'&&receipt.fresh===true&&receipt.replayed===false,'A fresh completed receipt is required.');
 ensure(receipt.alias===alias&&receipt.query_digest===query,'Receipt query or retriever does not match this request.');
 ensure(receipt.bundle_id===snapshot[alias].bundle_id&&receipt.admission_generation===snapshot[alias].generation&&receipt.completion_generation===snapshot[alias].generation,'The model alias changed during this suite. Start a new comparison.');
 for(const key of ['id','deployment_id','corpus_digest','graph_digest','tokenizer_digest','index_digest'] as const)ensure(typeof receipt[key]==='string'&&receipt[key].length>0,'Receipt artifact identity is missing.');
 ensure(Array.isArray(receipt.results)&&receipt.results.length===depth,'The result list is incomplete.');
 ensure(receipt.results.every(r=>typeof r.id==='string'&&typeof r.title==='string'&&typeof r.visible_text==='string'&&Number.isFinite(r.score)),'The result list contains an invalid document or score.');
 const ids=receipt.results.map(r=>r.id);
 ensure(new Set(ids).size===depth&&canonical(ids)===canonical(receipt.top_document_ids),'The result list has duplicate or mismatched document IDs.');
}
export function compareRankings(base:Receipt,learned:Receipt){
 ensure(base.query_digest===learned.query_digest,'Cannot compare different queries.');
 ensure(base.corpus_digest===learned.corpus_digest,'Cannot compare different corpus versions.');
 ensure(base.deployment_id===learned.deployment_id,'Deployment changed between requests. Start a new comparison.');
 ensure(base.id!==learned.id,'Independent request receipts are required.');
 const depth=base.results.length;
 ensure(depth>0&&depth===learned.results.length,'Comparison depths do not match.');
 const a=new Map(base.results.map((r,i)=>[r.id,{...r,rank:i+1}]));
 const b=new Map(learned.results.map((r,i)=>[r.id,{...r,rank:i+1}]));
 ensure(a.size===depth&&b.size===depth,'Duplicate document IDs cannot be compared.');
 const shared=[...a.keys()].filter(id=>b.has(id));
 const rows:RankedDocument[]=[...new Set([...a.keys(),...b.keys()])].map(id=>({id,title:(b.get(id)||a.get(id))!.title,base_rank:a.get(id)?.rank??null,learned_rank:b.get(id)?.rank??null,rank_change:a.has(id)&&b.has(id)?a.get(id)!.rank-b.get(id)!.rank:null,rrf_score:(a.has(id)?1/(60+a.get(id)!.rank):0)+(b.has(id)?1/(60+b.get(id)!.rank):0)}));
 rows.sort((x,y)=>y.rrf_score-x.rrf_score||order(x.id,y.id));
 return {depth,shared:shared.length,jaccard:shared.length/(depth*2-shared.length),mean_shared_rank_shift:shared.length?shared.reduce((n,id)=>n+Math.abs(a.get(id)!.rank-b.get(id)!.rank),0)/shared.length:null,rows,rrf_constant:60};
}

/** Serial requests preserve one-active-request-per-session; stop drains in-flight work. */
export async function executeSuite(queries:string[],depth:number,request:Request,onUpdate:(suite:Suite)=>void,shouldStop:()=>boolean,pause:()=>Promise<void>=()=>new Promise(resolve=>setTimeout(resolve,1000))):Promise<Suite>{
 ensure(depth===10||depth===20,'Choose a result depth of 10 or 20.');
 ensure(canonical(parseQueries(queries.join('\n')))===canonical(queries),'Invalid query inventory.');
 const suite:Suite={schema_version:1,namespace:'live_ranking_diagnostics',quality_claim:false,started_at:new Date().toISOString(),depth,planned:queries.length,status:'running',rows:await Promise.all(queries.map(async(q,index)=>({index,query_digest:await queryDigest(q),status:'pending',receipts:{},milliseconds:{}})))};
 onUpdate(suite);
 let token='';
 try{
  const models=await request('/api/v1/models');
  const snapshot={} as Snapshot;
  for(const alias of ['base','experimental'] as Alias[]){
   const row=models.aliases?.find((r:any)=>r.name===alias);
   ensure(row?.available===true&&row.valid===true&&typeof row.bundle_id==='string'&&Number.isInteger(row.generation),'Both retrievers must be available before comparison.');
   snapshot[alias]={bundle_id:row.bundle_id,generation:row.generation};
  }
  suite.snapshot=snapshot;
  if(!shouldStop()){
   token=(await request('/api/v1/sessions',{method:'POST'})).capability;
   ensure(typeof token==='string'&&token.length>0,'The public session could not be established.');
  }
  let sent=false;
  for(const row of suite.rows){
   if(shouldStop()){row.status='cancelled';continue;}
   row.status='running';onUpdate(suite);
   try{
    for(const alias of ['base','experimental'] as Alias[]){
     if(sent)await pause();
     if(shouldStop()){row.status='cancelled';break;}
     const started=performance.now();
     const receipt:Receipt=await request('/api/v1/search',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`,'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({query:queries[row.index],alias,top_k:depth})});
     sent=true;
     row.milliseconds[alias]=performance.now()-started;
     validateReceipt(receipt,alias,row.query_digest,depth,snapshot);
     const stored=await request('/api/v1/receipts/'+encodeURIComponent(receipt.id),{headers:{Authorization:`Bearer ${token}`}});
     ensure(canonical(stored)===canonical(receipt),'Persisted receipt differs from the search response.');
     row.receipts[alias]=receipt;onUpdate(suite);
    }
    if(row.receipts.base&&row.receipts.experimental){row.comparison=compareRankings(row.receipts.base,row.receipts.experimental);row.status='completed';}
   }catch(error){row.status='failed';row.error=error instanceof Error?error.message:'Request failed.';}
   onUpdate(suite);
   // A timeout or refusal can leave a server-side request active. Never send more on this session.
   if(row.status==='failed')break;
  }
 }catch(error){const row=suite.rows.find(r=>r.status==='pending');if(row){row.status='failed';row.error=error instanceof Error?error.message:'Setup failed.';}}
 finally{token='';}
 for(const row of suite.rows)if(row.status==='pending'||row.status==='running')row.status=shouldStop()?'cancelled':'not_run';
 suite.status=shouldStop()?'cancelled':suite.rows.every(r=>r.status==='completed')?'completed':'incomplete';
 suite.ended_at=new Date().toISOString();onUpdate(suite);return suite;
}
