import ast
import copy
import json
from pathlib import Path
import pytest
from model_atlas.analyzer import analyze
from model_atlas.validate import validate
from model_atlas.cli import node_tool, main
ROOT=Path(__file__).resolve().parents[1]

def demo(name='mha'):
    return analyze(ROOT/'examples/mini_decoder.py','MiniDecoder',ROOT/f'examples/configs/{name}.json',ROOT)

def test_reproducible_and_evidence():
    a,b=demo(),demo()
    assert a==b
    assert a['snapshot']['executed'] is False
    assert all(t['evidence'] for t in a['tensors'])
    assert not any(e['kind']=='runtime' for e in a['evidence'])
    assert {s['id'] for s in a['scopes']} >= {'model','blocks.0','blocks.0.attention','blocks.0.mlp'}
    assert all(s['bindings'] for s in a['scopes'] if s['parent'])

def test_teaching_shapes_and_parameters():
    a,b=demo(),demo('gqa')
    tensors=lambda doc:{t['name']:t['shape'] for t in doc['tensors']}
    for d in [a,b]:
        assert tensors(d)['q_proj']==['B','T',64]
        assert tensors(d)['logits']==['B','T',128]
        assert tensors(d)['k_repeat']==['B',8,'T',8]
    assert tensors(a)['k_proj']==['B','T',64]
    assert tensors(b)['k_proj']==['B','T',16]
    assert tensors(a)['k_transpose']==['B',8,'T',8]
    assert tensors(b)['k_transpose']==['B',2,'T',8]
    assert a['snapshot']['parameterCount']-b['snapshot']['parameterCount']==12288
    for layer in [0,1]:
        count=lambda doc:sum(p['count'] for p in doc['parameters'] if any(p['name'].startswith(f'blocks.{layer}.attention.{x}_proj') for x in ['k','v']))
        assert count(a)-count(b)==6144
    c=node_tool('compare',dict(left=a,right=b))
    assert c['summary']['parameterDelta']==-12288
    assert c['summary']['theoreticalCache']['ratio']==.25
    assert [x['type'] for x in c['differences']].count('configuration')==1

def test_generic_temp_model_no_import(tmp_path):
    marker=tmp_path/'executed'
    code=f'''from torch import nn\nfrom pathlib import Path\nPath({str(marker)!r}).write_text('BAD')\nclass UnexpectedName(nn.Module):\n def __init__(self,c):\n  self.l = nn.Linear(4,4,bias=False)\n def forward(self,x):\n  h=self.l(x)\n  h=nn.functional.relu(h)\n  return x+h\n'''
    # Functional namespace unsupported form is honestly opaque; supported F.relu below.
    code=code.replace('nn.functional.relu','F.relu')
    (tmp_path/'actual.py').write_text(code);(tmp_path/'c.json').write_text('{}')
    a=analyze(tmp_path/'actual.py','UnexpectedName',tmp_path/'c.json',tmp_path)
    assert not marker.exists()
    assert {'linear','relu','add'} <= {n['role'] for n in a['nodes']}
    assert a['snapshot']['parameterCount']==16
    addition=next(n for n in a['nodes'] if n['role']=='add')
    assert len([e for e in a['edges'] if next(p for p in a['ports'] if p['id']==e['target'])['node']==addition['id']])==2
    ref=next(r for r in a['sourceRefs'] if r['id']==addition['sourceRef'])
    assert 'return x + h' not in ref['snippet'] or ref['start']>0
    assert 'return x+h' in ref['snippet']
    assert a['tensors'][0]['unknownReason']

def test_adapter_change_hash_and_downgrade(tmp_path):
    source=tmp_path/'renamed.py';config=tmp_path/'c.json'
    text=(ROOT/'examples/mini_decoder.py').read_text()
    source.write_text(text);config.write_text((ROOT/'examples/configs/mha.json').read_text())
    a=analyze(source,'MiniDecoder',config,tmp_path)
    source.write_text(text.replace('scores = torch.matmul','scores = 2 * torch.matmul'))
    b=analyze(source,'MiniDecoder',config,tmp_path)
    assert a['snapshot']['sourceHash']!=b['snapshot']['sourceHash']
    assert any('失配' in l['reason'] for l in b['limitations'])
    assert not any(s['id']=='blocks.0.attention' for s in b['scopes'])
    assert b['snapshot']['parameterCount'] is None

def test_config_and_path_errors(tmp_path):
    source=tmp_path/'m.py';source.write_text((ROOT/'examples/mini_decoder.py').read_text())
    c=json.loads((ROOT/'examples/configs/mha.json').read_text());c['num_key_value_heads']=3
    config=tmp_path/'c.json';config.write_text(json.dumps(c))
    with pytest.raises(ValueError,match='整除'): analyze(source,'MiniDecoder',config,tmp_path)
    link=tmp_path/'outside.py';link.symlink_to(ROOT/'examples/mini_decoder.py')
    with pytest.raises(ValueError,match='越界'): analyze(link,'MiniDecoder',config,tmp_path)

def small(entry,tmp_path):
    c=tmp_path/'c.json';c.write_text('{}')
    return analyze(ROOT/'examples/small_models.py',entry,c,Path('/workspace') if str(tmp_path).startswith('/workspace') else Path('/'))

def test_shared_calls_branches_and_unused(tmp_path):
    d=small('BranchShared',tmp_path)
    linear=[n for n in d['nodes'] if n['role']=='linear']
    assert len(linear)==3
    assert linear[0]['instance']==linear[1]['instance']
    assert any(p['shared'] and len(p['instances'])==2 for p in d['parameters'])
    assert d['snapshot']['parameterCount']==24 # shared 16 + registered unused 8
    assert not any(n['instance']=='inst:unused' for n in d['nodes'])
    assert sum(n['role']=='output' for n in d['nodes'])==2
    assert any(n['role']=='cat' for n in d['nodes'])

def test_dynamic_and_heterogeneous_are_unknown(tmp_path):
    for entry in ['DynamicBranch','HeterogeneousRepeat']:
        d=small(entry,tmp_path)
        assert any(n['role']=='opaque' for n in d['nodes'])
        assert d['snapshot']['parameterCount'] is None
        assert d['views']==[]
        assert any('动态控制流' in x['reason'] for x in d['limitations'])

def test_validation_both_languages():
    a=demo()
    mutations=[]
    d=copy.deepcopy(a);d['edges'][0]['target']='missing';mutations.append(d)
    d=copy.deepcopy(a);d['scopes'][1]['bindings']=[];mutations.append(d)
    d=copy.deepcopy(a);d['parameters'][0]['count']=1;mutations.append(d)
    d=copy.deepcopy(a);d['nodes'].append(d['nodes'][0]);mutations.append(d)
    d=copy.deepcopy(a);d['tensors'][0]['shape']=[None];mutations.append(d)
    for d in mutations:
        with pytest.raises(ValueError): validate(d)
        with pytest.raises(ValueError): node_tool('validate',d)
    validate(a);node_tool('validate',a)
    for kind in ['session','comparison']:
        if kind=='session': d=dict(kind='session',schemaVersion='1.0',notes=[])
        else: d=node_tool('compare',dict(left=a,right=demo('gqa')))
        validate(d);node_tool('validate',d)

def test_attack_safe_embedding(tmp_path,monkeypatch):
    d=demo();d['sourceRefs'][0]['snippet']+='\n</script><script>window.PWNED=1</script>'
    inp=tmp_path/'a.json';out=tmp_path/'nested/page.html';inp.write_text(json.dumps(d))
    monkeypatch.setattr('sys.argv',['model-atlas','build','--input',str(inp),'--out',str(out)])
    assert main()==0
    text=out.read_text();assert '\\u003c/script\\u003e' in text
    assert '</script><script>window.PWNED' not in text
    (ROOT/'build/attack-fixture.html').write_text(text)


def test_unknown_registration_does_not_report_zero_parameters(tmp_path):
    (tmp_path/'c.json').write_text('{}')
    (tmp_path/'m.py').write_text("class Novel:\n def __init__(self,c):\n  if c['flag']: self.l=CustomLayer()\n def forward(self,x):\n  return self.l(x)\n")
    d=analyze(tmp_path/'m.py','Novel',tmp_path/'c.json',tmp_path)
    assert d['snapshot']['parameterCount'] is None
    assert any('构造器动态' in l['reason'] for l in d['limitations'])
    assert any(n['opaque'] for n in d['nodes'])

def test_partial_weight_sharing_is_not_double_counted_as_known(tmp_path):
    (tmp_path/'c.json').write_text('{}')
    (tmp_path/'m.py').write_text('from torch import nn\nclass WeightSharing:\n def __init__(self,c):\n  self.a=nn.Linear(4,4,bias=False)\n  self.b=nn.Linear(4,4,bias=False)\n  self.b.weight=self.a.weight\n def forward(self,x):\n  y=self.a(x)\n  return self.b(y)\n')
    d=analyze(tmp_path/'m.py','WeightSharing',tmp_path/'c.json',tmp_path)
    assert d['snapshot']['parameterCount'] is None
    assert any('复杂共享' in l['reason'] for l in d['limitations'])

def test_unrelated_class_source_not_embedded(tmp_path):
    (tmp_path/'c.json').write_text('{}')
    (tmp_path/'m.py').write_text('class Unrelated:\n secret="do not embed unrelated data"\nclass Chosen:\n def forward(self,x):\n  return x\n')
    d=analyze(tmp_path/'m.py','Chosen',tmp_path/'c.json',tmp_path)
    assert not any('do not embed unrelated data' in s['snippet'] for s in d['sourceRefs'])
    assert [x['symbol'] for x in d['definitions']]==['Chosen']
