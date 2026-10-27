"""Application-owned CRUD source templates; user/model strings are encoded as data."""

SERVER = r"""from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, re, sqlite3, math
CONFIG = json.loads(__CONFIG__)
STRICT = __STRICT__
DB = os.getenv('WORKSPACE_DB', str(Path(__file__).with_name('workspace.sqlite')))
def connection():
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
    return db
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def reply(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path == '/':
            raw = Path(__file__).with_name('index.html').read_bytes()
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
        elif self.path == '/records':
            with connection() as db:
                records = [dict(id=row[0], **json.loads(row[1])) for row in db.execute('SELECT id,body FROM records ORDER BY id DESC')]
            self.reply(200,records)
        else: self.reply(404,{'error':'Not found'})
    def body(self):
        size = int(self.headers.get('Content-Length','0'))
        if not 0 < size <= 8000: raise ValueError('Request too large')
        body = json.loads(self.rfile.read(size))
        if not isinstance(body,dict): raise ValueError('Object required')
        fields = {'name','notes',CONFIG['field']}
        if STRICT:
            if set(body)-fields: raise ValueError('Unknown field')
            if not isinstance(body.get('name'),str) or not body['name'].strip() or len(body['name'])>200: raise ValueError('Name is required (max 200 characters)')
            if not isinstance(body.get('notes',''),str) or len(body.get('notes',''))>2000: raise ValueError('Notes too long')
            value = body.get(CONFIG['field'])
            if CONFIG['kind']=='tasks' and value not in ['todo','doing','done']: raise ValueError('Invalid task status')
            if CONFIG['kind']=='inventory' and (type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1e9): raise ValueError('Quantity must be a finite nonnegative number')
            if CONFIG['kind']=='contacts' and (not isinstance(value,str) or len(value)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value)): raise ValueError('Valid email required')
        return {key:body.get(key,'') for key in fields}
    def do_POST(self):
        if self.path!='/records': return self.reply(404,{'error':'Not found'})
        try:
            body = self.body()
            with connection() as db:
                if db.execute('SELECT COUNT(*) FROM records').fetchone()[0]>=10000: raise ValueError('Record limit reached')
                record_id = db.execute('INSERT INTO records(body) VALUES (?)',(json.dumps(body),)).lastrowid
            self.reply(201,dict(id=record_id,**body))
        except (ValueError,TypeError): self.reply(400,{'error':'Invalid record; check required fields and supported values'})
    def do_PUT(self):
        if not re.fullmatch(r'/records/[0-9]+',self.path): return self.reply(404,{'error':'Not found'})
        try:
            body=self.body()
            with connection() as db:
                updated=db.execute('UPDATE records SET body=? WHERE id=?',(json.dumps(body),int(self.path.split('/')[-1]))).rowcount
            self.reply(200 if updated else 404,{'updated':bool(updated)})
        except (ValueError,TypeError): self.reply(400,{'error':'Invalid record'})
    def do_DELETE(self):
        if not re.fullmatch(r'/records/[0-9]+',self.path): return self.reply(404,{'error':'Not found'})
        with connection() as db:
            deleted=db.execute('DELETE FROM records WHERE id=?',(int(self.path.split('/')[-1]),)).rowcount
        self.reply(200 if deleted else 404,{'deleted':bool(deleted)})
if __name__=='__main__':
    with connection(): pass
    ThreadingHTTPServer(('127.0.0.1',8080),Handler).serve_forever()
"""
HTML = r"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>__TITLE__</title><style>body{background:#101917;color:#e6eddf;font:16px system-ui;max-width:1100px;padding:36px;margin:auto}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #42543c;padding:20px 0}small{color:#9bb18b}h1{font-weight:500;font-size:36px}form{display:flex;gap:12px;flex-wrap:wrap;margin:30px 0}input,select,button{font:inherit;border:1px solid #506747;padding:12px;border-radius:6px;background:#19271f;color:inherit}button{cursor:pointer;background:#c6ef9f;color:#172510}label{display:grid;gap:8px;font-size:12px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:16px;border-bottom:1px solid #34472e}td:last-child{display:flex;gap:8px}td button{padding:7px;font-size:12px}#notice{min-height:24px;color:#c6ef9f}footer{margin-top:40px;color:#78906a;font-size:12px}@media(max-width:650px){body{padding:18px}table{font-size:12px}th,td{padding:10px}input{max-width:240px}}</style><header><div><small>PRAXIS / VERIFIED WORKSPACE</small><h1>__TITLE__</h1></div><small id="count"></small></header><form id="editor"><label>Name<input name="name" required maxlength="200"></label><label id="valueLabel"></label><label>Notes<input name="notes" maxlength="2000"></label><button id="save">Add record</button><button type="button" id="reset">Clear</button></form><p id="notice" role="status"></p><table><thead><tr><th>Name</th><th id="fieldTitle"></th><th>Notes</th><th>Actions</th></tr></thead><tbody id="records"></tbody></table><footer>Local SQLite persistence · Generated and tested by PRAXIS · No external services</footer><script>
const config=__CONFIG_JSON__;let editing=null;const form=document.querySelector('form');const field=config.field;
const control=document.createElement(config.kind==='tasks'?'select':'input');control.name=field;control.required=true;
if(config.kind==='tasks'){for(const status of ['todo','doing','done']){const option=document.createElement('option');option.value=status;option.textContent=status;control.append(option)}}else{control.type=config.kind==='inventory'?'number':'email';if(config.kind==='inventory'){control.min='0';control.step='any'}}
document.querySelector('#valueLabel').append(document.createTextNode(field[0].toUpperCase()+field.slice(1)),control);document.querySelector('#fieldTitle').textContent=field;
const notice=document.querySelector('#notice');async function request(path,method='GET',body){const r=await fetch(path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d}
function reset(){editing=null;form.reset();document.querySelector('#save').textContent='Add record'}document.querySelector('#reset').onclick=reset;
async function load(){try{const rows=await request('/records');document.querySelector('#count').textContent=rows.length+' records';const target=document.querySelector('#records');target.replaceChildren();for(const row of rows){const tr=document.createElement('tr');for(const key of ['name',field,'notes']){const td=document.createElement('td');td.textContent=String(row[key]);tr.append(td)}const actions=document.createElement('td');for(const action of ['Edit','Delete']){const button=document.createElement('button');button.textContent=action;button.onclick=async()=>{try{if(action==='Edit'){editing=row.id;for(const key of ['name',field,'notes'])form.elements.namedItem(key).value=row[key];document.querySelector('#save').textContent='Save changes';form.elements.name.focus()}else{await request('/records/'+row.id,'DELETE');await load()}}catch(e){notice.textContent=e.message}};actions.append(button)}tr.append(actions);target.append(tr)}}catch(e){notice.textContent=e.message}}
form.onsubmit=async e=>{e.preventDefault();try{const body=Object.fromEntries(new FormData(form));if(config.kind==='inventory')body[field]=Number(body[field]);await request(editing?'/records/'+editing:'/records',editing?'PUT':'POST',body);notice.textContent=editing?'Record updated.':'Record created.';reset();await load()}catch(e){notice.textContent=e.message}};load();
</script></html>"""
TEST = r"""import json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path
config=json.loads(__CONFIG__)
environment={**os.environ,'WORKSPACE_DB':'/tmp/workspace-test.sqlite'}
p=subprocess.Popen([sys.executable,'-B',str(Path(__file__).with_name('server.py'))],env=environment)
checks=[]
def request(path,method='GET',body=None):
    req=urllib.request.Request('http://127.0.0.1:8080'+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Content-Type':'application/json'})
    try:
        response=urllib.request.urlopen(req,timeout=3)
        return response.status,json.loads(response.read())
    except urllib.error.HTTPError as exc:return exc.code,json.loads(exc.read())
try:
    for i in range(60):
        try:request('/records');break
        except OSError:time.sleep(.05)
    else:raise AssertionError('Server did not start')
    field=config['field'];value={'tasks':'todo','inventory':7,'contacts':'hello@example.org'}[config['kind']]
    valid={'name':'Independent test record',field:value,'notes':'Verified HTTP CRUD'}
    status,created=request('/records','POST',valid);checks.append({'case':'create','passed':status==201})
    status,rows=request('/records');checks.append({'case':'read','passed':status==200 and any(r['id']==created.get('id') and r['name']==valid['name'] for r in rows)})
    valid['name']='Updated record';status,_=request('/records/'+str(created.get('id')),'PUT',valid);status,rows=request('/records');checks.append({'case':'update','passed':any(r['id']==created.get('id') and r['name']=='Updated record' for r in rows)})
    status,_=request('/records/'+str(created.get('id')),'DELETE');checks.append({'case':'delete','passed':status==200})
    invalid={**valid,'name':''};status,_=request('/records','POST',invalid);checks.append({'case':'reject empty name','passed':status==400})
    invalid={**valid,'untrusted_field':'rejected'};status,_=request('/records','POST',invalid);checks.append({'case':'reject unknown fields','passed':status==400})
    invalid={**valid,field:{'tasks':'not-a-status','inventory':-9,'contacts':'not-an-email'}[config['kind']]};status,_=request('/records','POST',invalid);checks.append({'case':'reject invalid typed value','passed':status==400})
    print(json.dumps({'passed':sum(c['passed'] for c in checks),'total':len(checks),'cases':checks}))
    raise SystemExit(0 if all(c['passed'] for c in checks) else 1)
finally:p.terminate();p.wait(timeout=3)
"""
VERIFY = r"""import os,sys,subprocess,time,json,urllib.request
from pathlib import Path
config=json.loads(__CONFIG__)
path='/tmp/persistence-check.sqlite';env={**os.environ,'WORKSPACE_DB':path}
def start():
 p=subprocess.Popen([sys.executable,'-B',str(Path(__file__).with_name('server.py'))],env=env)
 for _ in range(60):
  try:urllib.request.urlopen('http://127.0.0.1:8080/records',timeout=1);return p
  except OSError:time.sleep(.05)
 p.terminate();p.wait();raise AssertionError('Startup failed')
p=start()
try:
 field=config['field'];body={'name':'Persistent record',field:{'tasks':'done','inventory':3,'contacts':'persist@example.org'}[config['kind']],'notes':'Restart verification'}
 request=urllib.request.Request('http://127.0.0.1:8080/records',data=json.dumps(body).encode(),method='POST',headers={'Content-Type':'application/json'})
 created=json.load(urllib.request.urlopen(request));p.terminate();p.wait();p=start()
 rows=json.load(urllib.request.urlopen('http://127.0.0.1:8080/records'));assert any(row['id']==created['id'] and row['name']==body['name'] for row in rows)
 page=urllib.request.urlopen('http://127.0.0.1:8080/').read();assert config['title'].encode() in page or b'PRAXIS' in page
 print(json.dumps({'passed':2,'total':2,'checks':['SQLite persistence across process restart','HTML served']}))
finally:p.terminate();p.wait(timeout=3)
"""
