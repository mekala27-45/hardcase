type Item = Record<string, any>;
const html = (value:unknown) => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));

export function trainingChart(rows:Item[]):string {
 const values=rows.filter(r=>Number.isFinite(r.loss)&&Number.isFinite(r.update));
 if(!values.length)return '';
 const width=760,height=260,left=62,right=18,top=22,bottom=44;
 const maxX=Math.max(...values.map(r=>r.update)),maxY=Math.max(...values.map(r=>r.loss),.001)*1.05;
 const x=(v:number)=>left+v/maxX*(width-left-right),y=(v:number)=>height-bottom-v/maxY*(height-top-bottom);
 const arms=['uniform_contrastive','hard_contrastive','hard_distilled'];
 const lines=arms.map((arm,i)=>{const points=values.filter(r=>r.arm===arm).sort((a,b)=>a.update-b.update);return points.length?`<polyline points="${points.map(p=>`${x(p.update)},${y(p.loss)}`).join(' ')}" fill="none" stroke="var(--slot${i+1})" stroke-width="2" stroke-dasharray="${['none','6 3','2 3'][i]}"/>`:'';}).join('');
 return `<figure class="measured-chart"><figcaption>Recorded optimizer loss. Raw values, no smoothing. Source: actual training step ledgers.</figcaption><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Training loss by optimizer update. The corresponding exact rows follow this chart."><line x1="${left}" x2="${width-right}" y1="${height-bottom}" y2="${height-bottom}" stroke="currentColor"/><line x1="${left}" x2="${left}" y1="${top}" y2="${height-bottom}" stroke="currentColor"/>${[0,.5,1].map(t=>`<text x="${left-10}" y="${y(maxY*t)+4}" text-anchor="end">${(maxY*t).toFixed(2)}</text><line x1="${left}" x2="${width-right}" y1="${y(maxY*t)}" y2="${y(maxY*t)}" stroke="var(--line)"/>`).join('')}${lines}<text x="${left}" y="${height-20}">0</text><text x="${width-right}" y="${height-20}" text-anchor="end">${maxX}</text><text x="${width/2}" y="${height-6}" text-anchor="middle">Optimizer update</text><text x="${left}" y="14">Loss</text></svg></figure>`;
}

export function qualityChart(methods:Item[],primary?:Item):string {
 const rows=methods.filter(r=>r.status==='completed'&&Number.isFinite(r.ndcg10));
 if(!rows.length)return '';
 const width=760,left=190,right=70,height=rows.length*42+50;
 return `<figure class="measured-chart"><figcaption>Held-out mean nDCG@10. Axis 0 to 1. Only complete methods are plotted.</figcaption><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Complete method nDCG at ten. Exact method values and denominators appear in the following table.">${rows.map((r,i)=>`<text x="${left-12}" y="${28+i*42}" text-anchor="end">${html(r.method)}</text><rect x="${left}" y="${10+i*42}" width="${r.ndcg10*(width-left-right)}" height="24" fill="var(--slot${i+1})"/><text x="${left+r.ndcg10*(width-left-right)+10}" y="${28+i*42}">${r.ndcg10.toFixed(4)}</text>`).join('')}<text x="${left}" y="${height-8}">0</text><text x="${width-right}" y="${height-8}" text-anchor="end">1</text></svg>${primary?.status==='completed'?`<p>Paired candidate minus base: ${primary.estimate.mean_difference.toFixed(4)}; grouped interval [${primary.estimate.lower.toFixed(4)}, ${primary.estimate.upper.toFixed(4)}]. ${primary.estimate.queries} queries in ${primary.estimate.groups} groups; ${primary.estimate.resamples} resamples. Source: frozen evaluation report.</p>`:''}</figure>`;
}
