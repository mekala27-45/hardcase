/** Two authored query pairs against the public API; Node 24 native type stripping. */
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {executeSuite} from '../site/src/comparison.ts';

const base='https://hardcase-taupe.vercel.app';
const queries=['How do cells repair DNA after oxidative stress?','How does autophagy regulate mitochondrial function?'];
const request=async(path,options={})=>{
 const response=await fetch(base+path,{...options,signal:AbortSignal.timeout(12000)});
 const body=await response.json();
 if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:body.reason||'HTTP '+response.status);
 return body;
};
const suite=await executeSuite(queries,10,request,()=>{},()=>false);
const moduleBytes=await readFile(new URL('../site/src/comparison.ts',import.meta.url));
const evidence={...suite,source_commit:process.env.GITHUB_SHA||'local',module_sha256:createHash('sha256').update(moduleBytes).digest('hex'),observer:'Independent Node HTTPS client executing the comparison module; not browser evidence',queries_origin:'Two authored diagnostic examples; not benchmark quality labels'};
await mkdir('evidence/comparison',{recursive:true});
await writeFile('evidence/comparison/live-runtime.json',JSON.stringify(evidence,null,2)+'\n');
console.log(JSON.stringify({status:suite.status,planned:suite.planned,completed:suite.rows.filter(r=>r.status==='completed').length,errors:suite.rows.filter(r=>r.error).map(r=>({index:r.index,error:r.error}))}));
if(suite.status!=='completed')process.exitCode=1;
