"""Bounded software synthesis templates. No unrestricted shell or model code."""

BASELINE = """def evaluate(expression):
    parts = expression.split('+')
    return sum(float(part.strip()) for part in parts)
"""
CALCULATOR = """import ast
import math
import operator
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
def evaluate(expression):
    if not isinstance(expression, str) or len(expression) > 200:
        raise ValueError('Expression must be a string of at most 200 characters')
    def visit(node, depth=0):
        if depth > 20:
            raise ValueError('Expression is too deep')
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand, depth+1) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            value = OPS[type(node.op)](visit(node.left, depth+1), visit(node.right, depth+1))
        else:
            raise ValueError('Only numbers and + - * / parentheses are supported')
        if not math.isfinite(value) or abs(value) > 1e100:
            raise ValueError('Result is outside supported range')
        return value
    try:
        return visit(ast.parse(expression, mode='eval').body)
    except (SyntaxError, RecursionError, OverflowError) as exc:
        raise ValueError('Invalid arithmetic expression') from exc
"""
TESTS = """import importlib.util
import json
from pathlib import Path
spec = importlib.util.spec_from_file_location('calculator', Path(__file__).with_name('calculator.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cases = [('2+3', 5), ('12 - 7', 5), ('-2 * 3', -6), ('(2+3)*4', 20), ('1.5/0.5', 3)]
results = []
for expression, expected in cases:
    try:
        actual = module.evaluate(expression)
        passed = abs(actual - expected) < 1e-9
    except Exception:
        passed = False
    results.append({'case': expression, 'passed': passed})
for expression in ['__import__("os").system("id")', '2**100000', '1/0']:
    try:
        module.evaluate(expression)
        passed = False
    except (ValueError, ZeroDivisionError):
        passed = True
    except Exception:
        passed = False
    results.append({'case': 'reject: ' + expression, 'passed': passed})
print(json.dumps({'passed': sum(r['passed'] for r in results), 'total': len(results), 'cases': results}))
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
"""
SERVER = """from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
from calculator import evaluate
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/':
            self.send_error(404)
            return
        body = Path(__file__).with_name('index.html').read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body)
    def do_POST(self):
        if self.path != '/calculate':
            self.send_error(404)
            return
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 2048:
                raise ValueError('Invalid request size')
            expression = json.loads(self.rfile.read(size))['expression']
            response = {'result': evaluate(expression)}
            status = 200
        except (ValueError, KeyError, ZeroDivisionError, TypeError):
            response, status = {'error': 'Enter valid arithmetic using + - * / and parentheses.'}, 400
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 8080), Handler).serve_forever()
"""
HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>PRAXIS Calculator</title><style>body{background:#101719;color:#e8eae2;font:20px system-ui;max-width:600px;margin:15vh auto;padding:24px}input,button{font:inherit;padding:16px;border:1px solid #738a81;border-radius:8px}input{background:#1c2928;color:white;width:65%}button{background:#c9f590}output{display:block;font-size:36px;margin-top:32px}</style><h1>Precision, simply.</h1><p>A verified arithmetic workspace. Supports + − × ÷ and parentheses.</p><form id="calculator"><label for="expression">Expression</label><p><input id="expression" required maxlength="200" value="(2 + 3) * 4"><button>Evaluate</button></p></form><output id="result" aria-live="polite"></output><script>document.querySelector('form').onsubmit=async e=>{e.preventDefault();try{const r=await fetch('/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expression:document.querySelector('input').value})});const d=await r.json();document.querySelector('output').textContent=d.error||d.result}catch{document.querySelector('output').textContent='Server unavailable'}}</script></html>"""
HTTP_TEST = """import subprocess, urllib.request, json, time, sys
from pathlib import Path
p = subprocess.Popen([sys.executable, '-B', str(Path(__file__).with_name('server.py'))])
try:
    for attempt in range(50):
        try:
            page = urllib.request.urlopen('http://127.0.0.1:8080/', timeout=1).read()
            break
        except OSError:
            time.sleep(.05)
    else:
        raise AssertionError('Server did not start')
    assert b'Precision, simply.' in page
    request = urllib.request.Request('http://127.0.0.1:8080/calculate', data=json.dumps({'expression': '(2+3)*4'}).encode(), headers={'Content-Type':'application/json'})
    assert json.load(urllib.request.urlopen(request))['result'] == 20
    print(json.dumps({'passed': 2, 'total': 2, 'checks': ['HTML served', 'HTTP calculation equals 20']}))
finally:
    p.terminate()
    p.wait(timeout=3)
"""
