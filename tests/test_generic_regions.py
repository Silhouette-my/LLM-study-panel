"""Regression tests for the real failure: branches must not erase suffixes."""
from pathlib import Path
import pytest
from model_atlas.analyzer import analyze
from model_atlas.validate import validate
ROOT=Path(__file__).resolve().parents[1]


def extract(tmp_path, code, entry='DifferentName'):
    src=tmp_path/'actual.py';src.write_text(code)
    cfg=tmp_path/'config.json';cfg.write_text('{}')
    return analyze(src,entry,cfg,tmp_path)


def input_node(doc, port):
    p=next(p for p in doc['ports'] if p['id']==port)
    return next(n for n in doc['nodes'] if n['id']==p['node'])


def test_branch_suffix_and_two_outputs_preserved(tmp_path):
    d=extract(tmp_path,'''from torch import nn
class DifferentName(nn.Module):
 def __init__(self,c):
  self.layer=nn.Linear(4,4,bias=False)
 def forward(self,x,flag):
  if flag:
   h=x+1
  else:
   h=x*2
  y=self.layer(h)
  return h,y
''')
    assert sum(n['role']=='output' for n in d['nodes'])==2
    linear=next(n for n in d['nodes'] if n['role']=='linear')
    edge=next(e for e in d['edges'] if input_node(d,e['target'])['id']==linear['id'])
    assert input_node(d,edge['source'])['role']=='conditional_result'
    assert d['snapshot']['parameterCount'] is None
    assert any(e['condition'] for e in d['edges'])
    validate(d)


def test_reassigning_both_branches_does_not_invent_identity_bypass(tmp_path):
    d=extract(tmp_path,'''class DifferentName:
 def forward(self,x,flag):
  y=x
  if flag:
   y=x+1
  else:
   y=x*2
  return y
''')
    merge=next(n for n in d['nodes'] if n['role']=='conditional_result')
    incoming=[e for e in d['edges'] if input_node(d,e['target'])['id']==merge['id']]
    assert len(incoming)==1 # no path retaining the old y in this if/else
    assert input_node(d,incoming[0]['source'])['role']=='opaque'


def test_loop_keeps_suffix_but_does_not_fake_layer_instances(tmp_path):
    d=extract(tmp_path,'''class DifferentName:
 def forward(self,x,layers):
  for layer in layers:
   x=layer(x)
  y=x+1
  return y,x
''')
    assert any(n['role']=='add' for n in d['nodes'])
    assert sum(n['role']=='output' for n in d['nodes'])==2
    assert d['views']==[]
    assert not any(i['path'].startswith('layers.') for i in d['instances'])


def test_early_return_not_discarded_or_claimed_unconditional(tmp_path):
    d=extract(tmp_path,'''class DifferentName:
 def forward(self,x,flag):
  if flag:
   return x*2
  y=x+1
  return y
''')
    assert sum(n['role']=='output' for n in d['nodes'])==2
    assert any('未提前返回' in (e['condition'] or '') for e in d['edges'])
    assert any(n['label'].startswith('条件返回') for n in d['nodes'])


def test_context_modules_sequential_bounds_and_no_model_execution(tmp_path):
    marker=tmp_path/'side-effect'
    d=extract(tmp_path,f'''from torch import nn
from pathlib import Path
Path({str(marker)!r}).write_text('BAD')
class DifferentName(nn.Module):
 def __init__(self,c):
  with arbitrary_context():
   self.scorer=nn.Sequential(nn.Linear(4,4,bias=False),nn.GELU(),nn.Linear(4,1,bias=False))
 def forward(self,x):
  return self.scorer(x).squeeze(-1).float()
''')
    assert not marker.exists()
    assert len(d['scopes'])==2
    seq=next(n for n in d['nodes'] if n['role']=='sequential')
    child=next(s for s in d['scopes'] if s['id']==seq['childScope'])
    assert len(child['bindings'])==2
    assert d['snapshot']['parameterCount'] is None # context effects unverified
    cast=next(n for n in d['nodes'] if n['role']=='cast')
    incoming=[e for e in d['edges'] if input_node(d,e['target'])['id']==cast['id']]
    assert len(incoming)==1
    assert input_node(d,incoming[0]['source'])['role']=='squeeze'
    validate(d)


def test_plain_sequential_params_and_unknown_rank(tmp_path):
    d=extract(tmp_path,'''from torch import nn
class DifferentName(nn.Module):
 def __init__(self,c):
  self.block=nn.Sequential(nn.Linear(4,4,bias=False),nn.GELU(),nn.Linear(4,1,bias=False))
 def forward(self,x):
  return self.block(x)
''')
    assert d['snapshot']['parameterCount']==20
    assert all(t['shape']==[None] for t in d['tensors']) # no invented 2D/3D rank
    assert {n['role'] for n in d['nodes']} >= {'linear','gelu','sequential'}
    assert any('末维为 1' in e['calculation'] for e in d['explanations'])


def test_laya_excerpt_after_all_conditionals_is_retained(tmp_path):
    source=ROOT/'tests/fixtures/laya_decision_excerpt.py'
    cfg=tmp_path/'cfg.json';cfg.write_text('{}')
    d=analyze(source,'DecisionModel',cfg,Path('/'))
    assert d['snapshot']['executed'] is False
    assert d['snapshot']['parameterCount'] is None
    assert len(d['scopes'])==3
    assert {'encoder','head','type_emb','scorer','act_head'} <= {i['path'] for i in d['instances']}
    assert not any(i['path']=='temperature' for i in d['instances']) # a buffer, not a module
    assert {'self.scorer','self.act_head'} <= {n['label'] for n in d['nodes']}
    assert any(n['role']=='gather' for n in d['nodes'])
    outputs=[n['label'] for n in d['nodes'] if n['role']=='output' and n['scope']=='model']
    assert outputs==['输出 logits','输出 act_logits']
    assert sum(n['opaque'] and n['role']=='opaque' for n in d['nodes'])>=5
    assert all(not n['childScope'] for n in d['nodes'] if n['label']=='self.encoder')
    assert not any('Attention' in s['label'] for s in d['scopes'])
    assert d['views']==[] # no assumed head_layers or encoder layer count
    for n in d['nodes']:
        r=next(r for r in d['sourceRefs'] if r['id']==n['sourceRef'])
        assert r['start']>=574
