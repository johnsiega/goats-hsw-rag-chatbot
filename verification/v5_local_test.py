import ast, hashlib, json, os, time, types, unittest.mock as mock
import urllib.request
from pathlib import Path
p=Path('app.py'); s=p.read_text(encoding='utf-8'); tree=ast.parse(s)
ns={'os':os,'json':json,'time':time,'urllib':__import__('urllib'),'GROQ_MODEL':'openai/gpt-oss-20b','GROQ_TEMPERATURE':0,'GROQ_MAX_COMPLETION_TOKENS':1500,'GROQ_REASONING_EFFORT':'low','GROQ_TIMEOUT_S':45,'MAX_WAIT_S':8}
for n in tree.body:
 if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ('Busy','call_openrouter_once','call_groq'):
  exec(compile(ast.Module(body=[n],type_ignores=[]),str(p),'exec'),ns)
class P:
 def record(self,x): pass
ns['pacer']=P()
ns['_call_groq_direct']=lambda m,w: (_ for _ in ()).throw(ns['Busy']('daily'))
class Response:
 def __enter__(self): return self
 def __exit__(self,*a): pass
 def read(self,*a): return b'{"choices":[{"message":{"content":"OK"}}],"usage":{"prompt_tokens":2,"completion_tokens":3}}'
def urlopen(req,timeout):
 body=json.loads(req.data); assert body['provider']=={'order':['groq'],'allow_fallbacks':False}; assert body['reasoning']=={'effort':'low'}; assert body['max_completion_tokens']==1500; assert body['messages'][0]['content']=='SYSTEM'; assert timeout==45
 return Response()
with mock.patch.dict(os.environ,{'OPENROUTER_API_KEY':'dummy'}), mock.patch.object(ns['urllib'].request,'urlopen',urlopen):
 assert ns['call_groq']([{'role':'system','content':'SYSTEM'}])['text']=='OK'
ns['_call_groq_direct']=lambda m,w:{'text':'PRIMARY'}
assert ns['call_groq']([])['text']=='PRIMARY'
ns['_call_groq_direct']=lambda m,w: (_ for _ in ()).throw(ns['Busy']('pacer'))
try: ns['call_groq']([])
except ns['Busy'] as e: assert str(e)=='pacer'
else: raise AssertionError('pacer incorrectly fell back')
ns2={'DOMAIN_NAME':''}; exec(s[s.index('REFUSAL_SENTENCE ='):s.index('# ---------------------------------------------------------------- index')],ns2)
assert hashlib.sha256(ns2['PROMPTS']['STRICT_V2'].encode()).hexdigest()=='e5236f33c55a8660c601223ff3f2979f407fe25d14799e3b3e0e889c48650d6a'
print('local fallback, primary, pacer, prompt hash: PASS')
