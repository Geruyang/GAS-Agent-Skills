import {readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const external=path.resolve(root,'../../.gas/experiments/xiangqi-v2/external');
const measured=JSON.parse(await readFile(path.join(external,'measurement.json'),'utf8'));
const hash=data=>createHash('sha256').update(data).digest('hex');
const result={checked_at:new Date().toISOString(),observer:'/root',governance_role:null,measurement_at:measured.measured_at,common_contract_unchanged:hash(await readFile(path.join(root,'CONTRACT.md')))===measured.contract_sha256,common_tests_unchanged:hash(await readFile(path.join(root,'tests/acceptance.test.mjs')))===measured.test_sha256,modes:{}};
for(const [mode,data] of Object.entries(measured.modes)){
 const items=await readdir(path.join(root,mode),{withFileTypes:true});
 const paths=items.map(i=>i.name).sort();
 const checks=[];
 for(const f of data.files){checks.push({path:f.path,unchanged:hash(await readFile(path.join(root,mode,f.path)))===f.sha256});}
 result.modes[mode]={same_inventory:JSON.stringify(paths)===JSON.stringify(data.files.map(f=>f.path).sort()),files:checks,external_test_evidence_current:checks.every(x=>x.unchanged)&&paths.length===data.files.length};
}
result.all_current=result.common_contract_unchanged&&result.common_tests_unchanged&&Object.values(result.modes).every(m=>m.same_inventory&&m.external_test_evidence_current);
await writeFile(path.join(external,'final-evidence-binding.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
if(!result.all_current)process.exitCode=1;
