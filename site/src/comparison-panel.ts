import {executeSuite,parseQueries,type Suite,type Request} from './comparison';

let input='',depth=10,suite:Suite|null=null,busy=false,stopping=false,selected=0;
let message='Compare the pretrained baseline and learned candidate on your own queries.';
const esc=(v:unknown)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const number=(v:number|undefined)=>v===undefined?'Not measured':v.toFixed(1);

export function comparisonView(){return `<section class="intro compact"><div><p class="eyebrow">LIVE RANKING DIAGNOSTICS</p><h1>See where models disagree.</h1><p class="lead">Run the same queries through two frozen retrievers. Inspect rank changes and verify both execution receipts.</p></div><div class="specimen-note"><span>EXPLORATORY WORKBENCH</span><strong>No relevance labels</strong><p>Agreement measures similarity between lists. It does not establish which model is better.</p></div></section><section class="evidence-panel"><form id="comparison-form"><label for="comparison-queries">Queries, one per line</label><textarea id="comparison-queries" rows="4" aria-describedby="comparison-help" ${busy?'disabled':''} required>${esc(input)}</textarea><p id="comparison-help">One to eight queries, at most 512 characters each. Queries and session credentials stay out of saved reports. Reloading clears this workspace.</p><div class="comparison-actions"><label for="comparison-depth">Results per retriever<select id="comparison-depth" ${busy?'disabled':''}><option value="10" ${depth===10?'selected':''}>10 results</option><option value="20" ${depth===20?'selected':''}>20 results</option></select></label><button type="submit" class="primary" id="comparison-run" ${busy?'disabled':''}>Run comparison</button><button type="button" id="comparison-example" ${busy?'disabled':''}>Load two example queries</button><button type="button" id="comparison-stop" ${!busy||stopping?'disabled':''}>Stop after current request</button></div></form><p id="comparison-status" role="status" aria-live="polite">${esc(message)}</p></section><div id="comparison-output">${output()}</div>`;}

function output(){
 if(!suite)return '<div class="empty"><span class="eyebrow">NO PAIRED RUN YET</span><p>Each pair requires two fresh searches and two matching persisted receipts.</p></div>';
 const done=suite.rows.filter(r=>r.status==='completed').length;
 const row=suite.rows[selected];
 return `<section class="evidence-panel"><div class="section-head"><h2>${done} / ${suite.planned} pairs completed</h2><button id="comparison-download" ${busy?'disabled':''}>Download diagnostic report</button></div><p>State: ${esc(suite.status)}. Requests run sequentially with a one-second pause. Latencies are individual network observations, not a benchmark or capacity estimate.</p><div class="comparison-selector" role="group" aria-label="Query comparisons">${suite.rows.map(r=>`<button data-pair="${r.index}" aria-pressed="${selected===r.index}">Query ${r.index+1}: ${esc(r.status)}</button>`).join('')}</div>${row?`<article class="comparison-detail"><h3>Query ${row.index+1}</h3><p class="evidence-caption">Query fingerprint: ${esc(row.query_digest)}</p>${row.error?`<p class="comparison-error">${esc(row.error)}</p>`:''}${row.comparison?details(row):`<p>${row.status==='running'?'Waiting for both verified receipts.':row.status==='cancelled'?'Stopped. No complete pair is claimed.':'No complete pair is available.'}</p>`}<details><summary>Inspect both execution receipts</summary><p>Each displayed receipt has passed a separate persisted readback. Credentials and raw query text are excluded.</p><pre>${esc(JSON.stringify(row.receipts,null,2))}</pre></details></article>`:''}</section>`;
}
function details(row:Suite['rows'][number]){
 const c=row.comparison!;
 return `<dl class="comparison-metrics"><div><dt>Shared documents</dt><dd>${c.shared} / ${c.depth}</dd></div><div><dt>Jaccard overlap</dt><dd>${(100*c.jaccard).toFixed(1)}%</dd></div><div><dt>Mean shared rank shift</dt><dd>${c.mean_shared_rank_shift===null?'No shared documents':c.mean_shared_rank_shift.toFixed(2)}</dd></div><div><dt>Baseline / learned latency</dt><dd>${number(row.milliseconds.base)} / ${number(row.milliseconds.experimental)} ms</dd></div></dl><p>Rank change is baseline rank minus learned rank. Positive values mean a document moved upward. A missing rank means outside the returned list, not irrelevant.</p><div class="table-scroll" tabindex="0" role="region" aria-label="Paired ranking differences"><table><thead><tr><th scope="col">Document</th><th scope="col">Baseline rank</th><th scope="col">Learned rank</th><th scope="col">Rank change</th><th scope="col">RRF preview</th></tr></thead><tbody>${c.rows.map((r,i)=>`<tr><td><strong>${esc(r.title)}</strong><br>Document ${esc(r.id)}</td><td>${r.base_rank??'Outside list'}</td><td>${r.learned_rank??'Outside list'}</td><td>${r.rank_change===null?'Not paired':r.rank_change>0?'+'+r.rank_change:r.rank_change}</td><td>${i+1} (${r.rrf_score.toFixed(5)})</td></tr>`).join('')}</tbody></table></div><details><summary>How these diagnostic values are calculated</summary><p>Jaccard is shared documents divided by the union of both lists. Mean rank shift averages absolute rank changes over shared documents only. The reciprocal-rank fusion preview sums 1 / (60 + rank) across these two truncated lists, then sorts by score and document ID. It is calculated in this browser, not a newly served retriever, and has no measured relevance score.</p><p class="evidence-caption">Corpus ${esc(row.receipts.base!.corpus_digest)}<br>Deployment ${esc(row.receipts.base!.deployment_id)}</p></details>`;
}
function refresh(){
 const status=document.querySelector('#comparison-status');if(status)status.textContent=message;
 const target=document.querySelector('#comparison-output');if(target){target.innerHTML=output();wireOutput();}
 for(const id of ['comparison-run','comparison-queries','comparison-depth','comparison-example']){const control=document.getElementById(id) as HTMLButtonElement|HTMLInputElement|null;if(control)control.disabled=busy;}
 const stop=document.querySelector<HTMLButtonElement>('#comparison-stop');if(stop)stop.disabled=!busy||stopping;
}
function wireOutput(){
 document.querySelectorAll<HTMLButtonElement>('[data-pair]').forEach(button=>button.addEventListener('click',()=>{selected=Number(button.dataset.pair);refresh();}));
 document.querySelector('#comparison-download')?.addEventListener('click',()=>{
  if(!suite||busy)return;
  const data={...suite,limitations:['No relevance judgments or quality claim.','RRF is a browser-only preview over truncated lists.','Raw queries and credentials are omitted.','Failures and cancelled rows remain in the denominator.']};
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='hardcase-comparison.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 });
}
export function wireComparison(request:Request){
 document.querySelector<HTMLTextAreaElement>('#comparison-queries')?.addEventListener('input',event=>{input=(event.target as HTMLTextAreaElement).value;});
 document.querySelector<HTMLSelectElement>('#comparison-depth')?.addEventListener('change',event=>{depth=Number((event.target as HTMLSelectElement).value);});
 document.querySelector('#comparison-example')?.addEventListener('click',()=>{input='How do cells repair DNA after oxidative stress?\nHow does autophagy regulate mitochondrial function?';document.querySelector<HTMLTextAreaElement>('#comparison-queries')!.value=input;});
 document.querySelector('#comparison-stop')?.addEventListener('click',()=>{stopping=true;message='Stopping after the in-flight request settles. No additional searches will start.';refresh();});
 document.querySelector('#comparison-form')?.addEventListener('submit',async event=>{
  event.preventDefault();if(busy)return;
  let queries:string[];
  try{queries=parseQueries(input);}catch(error){message=(error as Error).message;refresh();return;}
  busy=true;stopping=false;selected=0;message='Capturing model identities and opening an isolated public session.';refresh();
  try{suite=await executeSuite(queries,depth,request,current=>{suite=current;if(!stopping)message=`${current.rows.filter(r=>r.status==='completed').length} of ${current.planned} verified pairs. ${current.status==='running'?'Running serial comparisons.':'Run '+current.status+'.'}`;refresh();},()=>stopping);}
  catch(error){message='Comparison unavailable. '+(error instanceof Error?error.message:'Please retry.');}
  finally{busy=false;if(suite)message=`Run ${suite.status}. ${suite.rows.filter(r=>r.status==='completed').length} of ${suite.planned} pairs completed. No relevance claim is made.`;refresh();}
 });
 wireOutput();
}
