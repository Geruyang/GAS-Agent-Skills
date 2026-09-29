import http from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.md':'text/plain; charset=utf-8','.png':'image/png'};
http.createServer(async(req,res)=>{
 try{
  const requestUrl=new URL(req.url,'http://localhost');
  const name=decodeURIComponent(requestUrl.pathname);
  let file=path.resolve(root,'.'+name);
  if(file!==root&&!file.startsWith(root+path.sep)){res.writeHead(403);res.end('Forbidden');return;}
  if((await stat(file)).isDirectory()){
   if(!requestUrl.pathname.endsWith('/')){
    res.writeHead(301,{'Location':requestUrl.pathname+'/'+requestUrl.search});res.end();return;
   }
   file=path.join(file,'index.html');
  }
  const data=await readFile(file);
  res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(data);
 }catch{res.writeHead(404,{'Content-Type':'text/plain'});res.end('Not found');}
}).listen(8765,'127.0.0.1',()=>console.log('Xiangqi comparison: http://127.0.0.1:8765'));
