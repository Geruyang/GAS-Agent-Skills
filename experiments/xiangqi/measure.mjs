// External experiment measurement. Does not write or judge any team's product.
import {readFile,readdir,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve(root,'../../.gas/experiments/xiangqi-v2/external');
await mkdir(out,{recursive:true});
const digest=s=>createHash('sha256').update(s).digest('hex');
const result={measured_at:new Date().toISOString(),node:process.version,platform:process.platform,measurement_role:'external-observer-only',contract_sha256:digest(await readFile(path.join(root,'CONTRACT.md'))),test_sha256:digest(await readFile(path.join(root,'tests/acceptance.test.mjs'))),modes:{}};
async function files(dir,prefix=''){const names=[];for(const d of await readdir(dir,{withFileTypes:true})){if(d.isDirectory())names.push(...await files(path.join(dir,d.name),prefix+d.name+'/'));else names.push(prefix+d.name);}return names.sort();}
for(const mode of ['centralized','decentralized','combined']){
 const info={files:[],code_lines:0,code_bytes:0};
 try{
  for(const rel of await files(path.join(root,mode))){const data=await readFile(path.join(root,mode,rel));info.files.push({path:rel,bytes:data.length,sha256:digest(data)});if(/\.(js|css|html|mjs)$/.test(rel)&&!/(test|spec)/.test(rel)){info.code_lines+=data.toString().split(/\r?\n/).length;info.code_bytes+=data.length;}}
  info.product_manifest_sha256=digest(info.files.map(f=>`${f.path}:${f.sha256}`).join('\n'));
  const started=performance.now();let log='';
  try{log=execFileSync(process.execPath,['--test','--test-reporter=tap','tests/acceptance.test.mjs'],{cwd:root,env:{...process.env,XIANGQI_MODE:mode},encoding:'utf8',timeout:120000});info.exit_code=0;}
  catch(err){info.exit_code=err.status??null;log=String(err.stdout??'')+'\n'+String(err.stderr??'');}
  info.common_test_ms=Number((performance.now()-started).toFixed(2));
  info.pass_count=log.match(/# pass (\d+)/)?Number(log.match(/# pass (\d+)/)[1]):null;info.fail_count=log.match(/# fail (\d+)/)?Number(log.match(/# fail (\d+)/)[1]):null;
  info.test_log=`${mode}-acceptance.txt`;await writeFile(path.join(out,info.test_log),log);
 }catch(err){info.error=err.message;}
 result.modes[mode]=info;
}
await writeFile(path.join(out,'measurement.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
