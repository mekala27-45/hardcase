type Item = Record<string, any>;
const html = (value:unknown) => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));

export function trainingChart(rows:Item[],claim?:Item):string {
 const values=rows.filter(r=>Number.isFinite(r.loss)&&Number.isFinite(r.update));
 if(!values.length)return '';
 const width=760,height=260,left=62,right=18,top=22,bottom=44;
 const maxX=Math.max(...values.map(r=>r.update)),maxY=Math.max(...values.map(r=>r.loss),.001)*1.05;
 const x=(v:number)=>left+v/maxX*(width-left-right),y=(v:number)=>height-bottom-v/maxY*(height-top-bottom);
 const arms=['uniform_contrastive','hard_contrastive','hard_distilled'];
 const lines=arms.map((arm,i)=>{const points=values.filter(r=>r.arm===arm).sort((a,b)=>a.update-b.update);return points.length?`<polyline points="${points.map(p=>`${x(p.update)},${y(p.loss)}`).join(' ')}" fill="none" stroke="var(--slot${i+1})" stroke-width="2" stroke-dasharray="${['none','6 3','2 3'][i]}"/>`:'';}).join('');
 return `<figure class="measured-chart"><figcaption>${html(claim?.title||'Recorded optimizer loss. Raw values, no smoothing.')}</figcaption><div class="chart-scroll" tabindex="0" role="region" aria-label="Measured chart; scroll horizontally for full labels"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Training loss by optimizer update. The corresponding exact rows follow this chart."><line x1="${left}" x2="${width-right}" y1="${height-bottom}" y2="${height-bottom}" stroke="currentColor"/><line x1="${left}" x2="${left}" y1="${top}" y2="${height-bottom}" stroke="currentColor"/>${[0,.5,1].map(t=>`<text x="${left-10}" y="${y(maxY*t)+4}" text-anchor="end">${(maxY*t).toFixed(2)}</text><line x1="${left}" x2="${width-right}" y1="${y(maxY*t)}" y2="${y(maxY*t)}" stroke="var(--line)"/>`).join('')}${lines}<text x="${left}" y="${height-20}">0</text><text x="${width-right}" y="${height-20}" text-anchor="end">${maxX}</text><text x="${width/2}" y="${height-6}" text-anchor="middle">Optimizer update</text><text x="${left}" y="14">Loss</text></svg></div></figure>`;
}

export function qualityChart(methods:Item[],primary?:Item):string {
 const rows=methods.filter(r=>r.status==='completed'&&Number.isFinite(r.ndcg10));
 if(!rows.length)return '';
 const width=760,left=190,right=70,height=rows.length*42+50;
 return `<figure class="measured-chart"><figcaption>${rows.map(r=>html(r.claim_title||r.method)).join('; ')}. Axis 0 to 1; complete methods only.</figcaption><div class="chart-scroll" tabindex="0" role="region" aria-label="Measured chart; scroll horizontally for full labels"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Complete method nDCG at ten. Exact method values and denominators appear in the following table."><defs><pattern id="base-hatch" width="7" height="7" patternUnits="userSpaceOnUse"><path d="M-1,1 l2,-2 M0,7 l7,-7 M6,8 l2,-2" stroke="var(--control)" stroke-width="2"/></pattern></defs>${rows.map((r,i)=>`<text x="${left-12}" y="${28+i*42}" text-anchor="end">${html(r.method)}</text><rect x="${left}" y="${10+i*42}" width="${r.ndcg10*(width-left-right)}" height="24" fill="${r.method==='base_encoder'?'url(#base-hatch)':r.method==='bm25'?'none':`var(--slot${({uniform_contrastive:1,hard_contrastive:2,hard_distilled:3,candidate_float32:4,candidate_int8:5} as Record<string,number>)[r.method]||1})`}" stroke="${r.method==='bm25'?'var(--control)':'none'}" stroke-dasharray="${r.method==='bm25'?'9 4':'none'}"/><text x="${left+r.ndcg10*(width-left-right)+10}" y="${28+i*42}">${r.ndcg10.toFixed(4)}</text>`).join('')}<text x="${left}" y="${height-8}">0</text><text x="${width-right}" y="${height-8}" text-anchor="end">1</text></svg></div>${primary?.status==='completed'?`<p>Paired candidate minus base: ${primary.estimate.mean_difference.toFixed(4)}; grouped interval [${primary.estimate.lower.toFixed(4)}, ${primary.estimate.upper.toFixed(4)}]. ${primary.estimate.queries} queries in ${primary.estimate.groups} groups; ${primary.estimate.resamples} resamples. Source: frozen evaluation report.</p>`:''}</figure>`;
}

export function pairedChart(rows:Item[]):string {
 const data=rows.filter(r=>Number.isFinite(r.difference)).sort((a,b)=>String(a.query_id).localeCompare(String(b.query_id)));
 if(!data.length)return '<p>No complete paired query observations are available.</p>';
 const width=760,height=240,left=58,right=20,top=24,bottom=35;
 const x=(i:number)=>left+i/Math.max(data.length-1,1)*(width-left-right),y=(v:number)=>top+(1-v)/2*(height-top-bottom);
 const svg='<svg viewBox="0 0 '+width+' '+height+'" role="img" aria-label="Per-query candidate minus base nDCG at ten"><line x1="'+left+'" x2="'+(width-right)+'" y1="'+y(0)+'" y2="'+y(0)+'" stroke="currentColor"/>'+[-1,0,1].map(v=>'<text x="'+(left-12)+'" y="'+(y(v)+4)+'" text-anchor="end">'+v+'</text>').join('')+data.map((r,i)=>'<circle cx="'+x(i)+'" cy="'+y(r.difference)+'" r="3" fill="'+(r.difference<0?'var(--negative)':r.difference>0?'var(--positive)':'var(--ink)')+'"><title>Query '+html(r.query_id)+': '+r.difference.toFixed(5)+'</title></circle>').join('')+'<text x="'+width/2+'" y="'+(height-5)+'" text-anchor="middle">Queries in stable ID order; exact rows below</text></svg>';
 return '<figure class="measured-chart"><figcaption>Paired nDCG@10 changes across '+data.length+' completed queries.</figcaption><div class="chart-scroll" tabindex="0" role="region" aria-label="Paired differences; scroll horizontally for full labels">'+svg+'</div></figure>';
}
