import json
from pathlib import Path
from importlib.resources import files
from jsonschema import Draft7Validator
MAX_BYTES = 12_000_000
MAX_NODES = 3000


def load(path):
    p = Path(path)
    if p.stat().st_size > MAX_BYTES:
        raise ValueError('文件超过 12 MB 限制')
    return json.loads(p.read_text(encoding='utf-8'))


def validate(doc):
    kind = doc.get('kind') if isinstance(doc, dict) else None
    if kind not in ('architecture', 'comparison', 'session'):
        raise ValueError('未知文档 kind')
    schema = json.loads(files('model_atlas').joinpath(f'resources/{kind}.schema.json').read_text())
    errors = sorted(Draft7Validator(schema).iter_errors(doc), key=lambda e: str(e.path))
    if errors:
        e = errors[0]
        raise ValueError(f'Schema /{"/".join(map(str,e.path))}: {e.message}')
    if kind == 'architecture':
        if len(doc['nodes']) > MAX_NODES:
            raise ValueError('图规模超过 3000 节点')
        tables = {}
        for k in ['definitions','instances','parameters','scopes','nodes','ports','edges','tensors','sourceRefs','evidence','claims','explanations','views']:
            tables[k] = {x['id']: x for x in doc[k]}
            if len(tables[k]) != len(doc[k]):
                raise ValueError(f'{k}: 重复 ID')
        roots=[s for s in doc['scopes'] if s['parent'] is None]
        if len(roots)!=1 or roots[0]['id']!='model' or roots[0]['owner'] is not None or not doc['nodes']:
            raise ValueError('必须包含唯一 model 根作用域和非空调用图')
        def get(k, key):
            if key not in tables[k]: raise ValueError(f'{k}: 悬空引用 {key}')
            return tables[k][key]
        for n in doc['nodes']:
            get('scopes',n['scope']); get('sourceRefs',n['sourceRef']); get('explanations',n['explanation'])
            if n['instance']: get('instances',n['instance'])
            if n['childScope']:
                child=get('scopes',n['childScope'])
                if child['owner'] != n['id'] or child['parent'] != n['scope']: raise ValueError('子作用域 owner/parent 不一致')
        for definition in doc['definitions']: get('sourceRefs',definition['sourceRef'])
        for view in doc['views']:
            for instance in view['instances']: get('instances',instance)
        for limitation in doc['limitations']:
            if limitation['sourceRef']: get('sourceRefs',limitation['sourceRef'])
            if limitation['scope']: get('scopes',limitation['scope'])
        for p in doc['ports']: get('nodes',p['node']); get('tensors',p['tensor'])
        for t in doc['tensors']:
            p=get('ports',t['producer'])
            if p['tensor']!=t['id'] or p['direction']!='out': raise ValueError('张量生产者不一致')
            for key in t['consumers']:
                p=get('ports',key)
                if p['tensor']!=t['id'] or p['direction']!='in': raise ValueError('张量消费者不一致')
            get('evidence',t['evidence'])
            if None in t['shape'] and not t['unknownReason']: raise ValueError('未知形状缺少原因')
        for e in doc['edges']:
            a,b=get('ports',e['source']),get('ports',e['target'])
            if a['direction']!='out' or b['direction']!='in' or a['tensor']!=e['tensor'] or b['tensor']!=e['tensor']: raise ValueError('边端口或张量不一致')
            for p in [a,b]:
                if get('nodes',p['node'])['scope']!=e['scope']: raise ValueError('边跨作用域：需显式绑定')
        for s in doc['scopes']:
            get('sourceRefs',s['sourceRef'])
            seen={s['id']}; cursor=s
            while cursor['parent']:
                cursor=get('scopes',cursor['parent'])
                if cursor['id'] in seen: raise ValueError('作用域环')
                seen.add(cursor['id'])
            for binding in s['bindings']:
                p,q=get('ports',binding['parentPort']),get('ports',binding['childPort'])
                if p['node']!=s['owner'] or get('nodes',q['node'])['scope']!=s['id']: raise ValueError('边界绑定归属错误')
                if p['direction']==q['direction']: raise ValueError('边界方向错误')
                if get('tensors',p['tensor'])['shape'] != get('tensors',q['tensor'])['shape']: raise ValueError('边界形状不一致')
            if s['owner']:
                get('nodes',s['owner'])
                if get('nodes',s['owner'])['childScope']!=s['id']: raise ValueError('owner 缺少反向作用域引用')
                owner_ports={p['id'] for p in doc['ports'] if p['node']==s['owner']}
                if owner_ports!={b['parentPort'] for b in s['bindings']}: raise ValueError('边界绑定不完整')
        for p in doc['parameters']:
            if p['count'] != __import__('math').prod(p['shape']): raise ValueError('参数 count 与形状不一致')
            for i in p['instances']: get('instances',i)
            get('evidence',p['evidence'])
            if p['shared'] != (len(p['instances'])>1): raise ValueError('共享参数标记不一致')
        for i in doc['instances']:
            if i['definition']: get('definitions',i['definition'])
            for p in i['parameterIds']:
                if i['id'] not in get('parameters',p)['instances']: raise ValueError('参数归属不一致')
        for e in doc['evidence']:
            for r in e['sourceRefs']: get('sourceRefs',r)
        for x in doc['explanations']+doc['claims']:
            for e in x['evidence']: get('evidence',e)
        total=sum(p['count'] for p in doc['parameters'])
        if doc['snapshot']['parameterCount'] is not None and doc['snapshot']['parameterCount']!=total: raise ValueError('参数总数不一致')
    elif kind == 'comparison':
        match_ids={m['id'] for m in doc['matches']}
        if len(match_ids)!=len(doc['matches']): raise ValueError('重复匹配 ID')
        for m in doc['matches']:
            if not m['left'] or not m['right']: raise ValueError('匹配两侧不得为空；未匹配由摘要记录')
            if any(len(set(m[side]))!=len(m[side]) for side in ['left','right']): raise ValueError('匹配组包含重复节点')
        for d in doc['differences']:
            if d['match'] and d['match'] not in match_ids: raise ValueError('差异引用未知匹配组')
    return doc
