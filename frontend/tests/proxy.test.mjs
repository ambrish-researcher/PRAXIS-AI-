import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import handler from '../api/[...path].js';
const nativeFetch=globalThis.fetch;
async function serve(callback){
 const server=http.createServer(handler);await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{return await callback(`http://127.0.0.1:${server.address().port}`);}finally{await new Promise(resolve=>server.close(resolve));}
}
test('proxy forwards same-origin API data and cookies to fixed configured HTTPS backend',async()=>{
 const old=process.env.PRAXIS_BACKEND_URL;process.env.PRAXIS_BACKEND_URL='https://backend.example';let target;
 globalThis.fetch=async(url,options)=>{target=String(url);assert.equal(options.headers.cookie,'praxis_session=signed');assert.equal(options.redirect,'manual');return new Response('{"status":"ok"}',{headers:{'Content-Type':'application/json','Set-Cookie':'praxis_session=updated; HttpOnly; Secure; SameSite=Lax'}});};
 try{await serve(async base=>{const r=await nativeFetch(base+'/api/health?test=1',{headers:{cookie:'praxis_session=signed'}});assert.equal(r.status,200);assert.equal((await r.json()).status,'ok');assert.match(r.headers.get('set-cookie'),/HttpOnly/);assert.equal(target,'https://backend.example/api/health?test=1');});}finally{globalThis.fetch=nativeFetch;if(old===undefined)delete process.env.PRAXIS_BACKEND_URL;else process.env.PRAXIS_BACKEND_URL=old;}
});
test('proxy rejects missing or insecure backend configuration before any upstream call',async()=>{
 const old=process.env.PRAXIS_BACKEND_URL;let calls=0;globalThis.fetch=async()=>{calls++;throw Error('must not call');};
 try{await serve(async base=>{delete process.env.PRAXIS_BACKEND_URL;assert.equal((await nativeFetch(base+'/api/health')).status,503);process.env.PRAXIS_BACKEND_URL='http://backend.example';assert.equal((await nativeFetch(base+'/api/health')).status,503);process.env.PRAXIS_BACKEND_URL='https://backend.example';assert.equal((await nativeFetch(base+'/private')).status,503);assert.equal(calls,0);});}finally{globalThis.fetch=nativeFetch;if(old===undefined)delete process.env.PRAXIS_BACKEND_URL;else process.env.PRAXIS_BACKEND_URL=old;}
});
test('proxy sanitizes upstream connection failures',async()=>{
 const old=process.env.PRAXIS_BACKEND_URL;process.env.PRAXIS_BACKEND_URL='https://backend.example';globalThis.fetch=async()=>{throw Error('private-server-error-should-not-leak');};
 try{await serve(async base=>{const r=await nativeFetch(base+'/api/health');assert.equal(r.status,502);assert.doesNotMatch(await r.text(),/private-server-error/);});}finally{globalThis.fetch=nativeFetch;if(old===undefined)delete process.env.PRAXIS_BACKEND_URL;else process.env.PRAXIS_BACKEND_URL=old;}
});
