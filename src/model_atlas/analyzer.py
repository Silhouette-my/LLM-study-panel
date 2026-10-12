"""只读取 AST。教学适配器按完整 AST 指纹校验；通用分析不执行代码。"""
import ast
import hashlib
import json
import math
from pathlib import Path
from importlib.resources import files
from .validate import validate, MAX_BYTES
from . import __version__


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def safe_path(path, root):
    root = Path(root).resolve()
    p = Path(path).resolve()
    if not p.is_relative_to(root): raise ValueError(f'路径越界: {path}')
    if p.suffix not in ('.py','.json'): raise ValueError('只读取 .py/.json')
    if p.stat().st_size > MAX_BYTES: raise ValueError('输入文件过大')
    return p


class Builder:
    def __init__(self, text, path, entry, config):
        self.tree=ast.parse(text); self.text=text; self.lines=text.splitlines(); self.path=path
        self.classes={x.name:x for x in self.tree.body if isinstance(x,ast.ClassDef)}
        self.doc=dict(kind='architecture',schemaVersion='1.0',snapshot=dict(id=digest(path+'\n'+text+json.dumps(config,sort_keys=True)+entry+__version__),model=entry,sourceHash=digest(text),config=config,mode='static',toolVersion=__version__,executed=False,parameterCount=None),**{k:[] for k in ['definitions','instances','parameters','scopes','nodes','ports','edges','tensors','sourceRefs','evidence','claims','explanations','views','limitations']})
        self.refs={}; self.symbols={}; self.outputs={}; self.module_instances={}
        for name,c in self.classes.items():
            self.symbols[name]=self.ref(name,c)
            self.doc['definitions'].append(dict(id='def:'+name,symbol=name,sourceRef=self.symbols[name]))

    def ref(self, symbol, node):
        key=(symbol,node.lineno,node.end_lineno)
        if key not in self.refs:
            ident=f'src:{symbol}:{node.lineno}:{node.end_lineno}'
            self.refs[key]=ident
            self.doc['sourceRefs'].append(dict(id=ident,path=self.path,symbol=symbol,start=node.lineno,end=node.end_lineno,hash=digest(self.text),snippet='\n'.join(self.lines[node.lineno-1:node.end_lineno])))
        return self.refs[key]

    def method_ref(self, cls, label=None):
        method=next(x for x in self.classes[cls].body if isinstance(x,ast.FunctionDef) and x.name=='forward')
        if label:
            for n in ast.walk(method):
                if isinstance(n,(ast.Assign,ast.Return)) and label in ast.unparse(n):
                    return self.ref(cls+'.forward',n)
        return self.ref(cls+'.forward',method)

    def evidence(self, ident, target, ref, text, kind='static'):
        key='ev:'+ident
        self.doc['evidence'].append(dict(id=key,kind=kind,target=target,sourceRefs=[ref],assumptions=['仅静态分析；B、T 为输入符号；浮点张量默认 float32'] if kind=='static' else [],text=text))
        return key

    def instance(self,path,cls,shapes,ref):
        ident='inst:'+path
        self.doc['instances'].append(dict(id=ident,path=path,definition='def:'+cls if cls in self.classes else None,config={**self.doc['snapshot']['config'],'moduleType':cls or '未确定'},parameterIds=[]))
        inst=self.doc['instances'][-1]
        for name,shape in shapes.items():
            p='param:'+path+'.'+name
            ev=self.evidence(p,'/parameters/'+str(len(self.doc['parameters'])),ref,'参数来自模块注册；按独立实体去重')
            self.doc['parameters'].append(dict(id=p,name=path+'.'+name,shape=shape,count=math.prod(shape),instances=[ident],shared=False,evidence=ev))
            inst['parameterIds'].append(p)
        return ident

    def scope(self, ident, label, cls, parent=None, owner=None):
        self.doc['scopes'].append(dict(id=ident,label=label,parent=parent,owner=owner,bindings=[],sourceRef=self.method_ref(cls)))
        return ident

    def node(self, scope, key, label, role, inputs, shape, ref, instance=None, child=None, dtype='float32', opaque=False, calculation=None):
        ident=scope+'/'+key; output=ident+':out'; tid=ident+':tensor'
        uncertain=opaque or None in shape
        ev=self.evidence(tid,'/tensors/'+str(len(self.doc['tensors']))+'/shape',ref,'有未确认的结构或形状维度，详见 unknownReason' if uncertain else '形状来自受支持运算和配置推导', 'unknown' if uncertain else 'static')
        fact=self.evidence('fact:'+ident,'/nodes/'+str(len(self.doc['nodes']))+'/sourceRef',ref,'该静态调用/运算对应 AST 源码位置；适配器子步骤可共享同一表达式范围','source')
        explanation='ex:'+ident
        self.doc['explanations'].append(dict(id=explanation,intuition={'add':'保留旁路信息，再加上本分支的变换。','softmax':'把当前允许关注的位置的分数转为权重。','repeat_kv':'将 KV 头复制到查询头数；存储前后的形状不同。','mul':'两个分支逐元素相乘。'}.get(role,'按实际源码读取该计算，选择边可核对依赖。'),calculation=calculation or f'输出形状 {shape}；B=batch，T=序列长度。未知尺寸不作猜测。',implementation='对应生成时源码快照；静态推导未做运行验证。',evidence=[fact,ev]))
        self.doc['nodes'].append(dict(id=ident,scope=scope,label=label,role=role,instance=instance,childScope=child,sourceRef=ref,explanation=explanation,opaque=opaque))
        for i,producer in enumerate(inputs):
            tensor=self.outputs[producer]
            pid=ident+f':in{i}'
            self.doc['ports'].append(dict(id=pid,node=ident,direction='in',name=f'input{i}',tensor=tensor))
            next(t for t in self.doc['tensors'] if t['id']==tensor)['consumers'].append(pid)
            self.doc['edges'].append(dict(id=ident+f':edge{i}',scope=scope,source=producer+':out',target=pid,tensor=tensor,condition=None))
        self.doc['ports'].append(dict(id=output,node=ident,direction='out',name='output',tensor=tid))
        reason=None
        if role=='input' and None in shape: reason='没有静态输入形状契约；未运行模型采样'
        elif opaque: reason='超出受限 AST 支持范围，保留边界'
        elif None in shape: reason='输入尺寸、广播或拼接条件未确认，不能推导完整形状'
        self.doc['tensors'].append(dict(id=tid,name=key,shape=shape,dtype=dtype,unknownReason=reason,producer=output,consumers=[],evidence=ev))
        self.outputs[ident]=tid
        return ident

    def bind(self, child, owner, input_node, output_node):
        scope=next(s for s in self.doc['scopes'] if s['id']==child)
        scope['bindings']=[dict(parentPort=owner+':in0',childPort=input_node+':out'),dict(parentPort=owner+':out',childPort=output_node+':in0')]

    def finish(self, complete):
        self.doc['snapshot']['parameterCount']=sum(p['count'] for p in self.doc['parameters']) if complete else None
        needed={'def:'+self.doc['snapshot']['model']}|{i['definition'] for i in self.doc['instances'] if i['definition']}
        self.doc['definitions']=[d for d in self.doc['definitions'] if d['id'] in needed]
        source_ids={x['sourceRef'] for key in ['definitions','scopes','nodes','limitations'] for x in self.doc[key] if x['sourceRef']}
        source_ids.update(r for e in self.doc['evidence'] for r in e['sourceRefs'])
        self.doc['sourceRefs']=[r for r in self.doc['sourceRefs'] if r['id'] in source_ids]
        return validate(self.doc)


def teaching(b,c):
    required={'vocab_size','hidden_size','intermediate_size','num_layers','num_attention_heads','num_key_value_heads','head_dim','projection_bias'}
    if set(c)!=required: raise ValueError('教学配置字段不完整或含未知字段')
    for k in required-{'projection_bias'}:
        if type(c[k]) is not int or not 0<c[k]<=1_000_000: raise ValueError(f'{k} 必须为正整数')
    if type(c['projection_bias']) is not bool: raise ValueError('projection_bias 必须是 bool')
    h,k,d,H,I,L,V=[c[x] for x in ['num_attention_heads','num_key_value_heads','head_dim','hidden_size','intermediate_size','num_layers','vocab_size']]
    if H!=h*d or h%k or k>h: raise ValueError('hidden_size=heads*head_dim 且 query heads 必须整除 KV heads')
    if L>32 or H>65536: raise ValueError('教学配置规模超过支持限制')
    shp=['B','T',H]; model=b.scope('model','MiniDecoder','MiniDecoder')
    def op(scope,key,role,inputs,shape,cls,label=None,inst=None,child=None,dtype='float32',calc=None):
        return b.node(scope,key,key,role,inputs,shape,b.method_ref(cls,label),inst,child,dtype,calculation=calc)
    def param(path,cls,shapes,module_type=None): return b.instance(path,module_type or cls,shapes,b.symbols[cls])
    def linear(path,out,cls):
        shapes={'weight':[out,H]}
        if cls=='Attention' and c['projection_bias']: shapes['bias']=[out]
        return param(path,cls,shapes,'torch.nn.Linear')
    root=param('model','MiniDecoder',{})
    tokens=op(model,'tokens','input',[],['B','T'],'MiniDecoder',dtype='int64')
    embed=param('embedding','MiniDecoder',{'weight':[V,H]},'torch.nn.Embedding')
    x=op(model,'embedding','embedding',[tokens],shp,'MiniDecoder','self.embedding(tokens)',embed)
    blocks=[]
    for index in range(L):
        path=f'blocks.{index}'; scope=path; inst=param(path,'DecoderBlock',{}); blocks.append(inst)
        owner=op(model,path,'decoder_block',[x],shp,'MiniDecoder','block(x)',inst,scope)
        b.scope(scope,f'Decoder Block {index}','DecoderBlock',model,owner)
        inp=op(scope,'x','input',[],shp,'DecoderBlock')
        n1=param(path+'.norm1','RMSNorm',{'weight':[H]})
        a=op(scope,'norm1','rmsnorm',[inp],shp,'DecoderBlock','self.norm1',n1)
        attention_scope=path+'.attention'; attinst=param(attention_scope,'Attention',{})
        att=op(scope,'attention','attention',[a],shp,'DecoderBlock','self.attention',attinst,attention_scope)
        b.scope(attention_scope,'Causal Self-Attention','Attention',scope,att)
        ai=op(attention_scope,'x','input',[],shp,'Attention')
        proj={}
        for name,size in [('q',H),('k',k*d),('v',k*d)]:
            inst=linear(attention_scope+'.'+name+'_proj',size,'Attention')
            p=op(attention_scope,name+'_proj','linear',[ai],['B','T',size],'Attention',f'{name} = self.{name}_proj',inst)
            reshape=op(attention_scope,name+'_reshape','reshape',[p],['B','T',h if name=='q' else k,d],'Attention',f'{name} = {name}.reshape')
            proj[name]=op(attention_scope,name+'_transpose','transpose',[reshape],['B',h if name=='q' else k,'T',d],'Attention',f'{name} = {name}.reshape')
        for name in ['k','v']:
            proj[name]=op(attention_scope,name+'_repeat','repeat_kv',[proj[name]],['B',h,'T',d],'Attention',f'{name} = {name}.repeat_interleave',calc=f'复制倍数 heads/kv_heads={h//k}；复制前 KV 头数 {k}，复制后 {h}。理论缓存按复制前存储估算。')
        kt=op(attention_scope,'k_score_transpose','transpose',[proj['k']],['B',h,d,'T'],'Attention','scores = torch.matmul')
        scores=op(attention_scope,'qk_scaled','matmul',[proj['q'],kt],['B',h,'T','T'],'Attention','scores = torch.matmul',calc=f'Q @ K^T / sqrt({d})')
        mask=op(attention_scope,'causal_mask','mask',[],['T','T'],'Attention','mask =',dtype='bool')
        masked=op(attention_scope,'masked_scores','masked_fill',[scores,mask],['B',h,'T','T'],'Attention','scores = scores.masked_fill')
        weights=op(attention_scope,'softmax','softmax',[masked],['B',h,'T','T'],'Attention','weights =')
        ctx=op(attention_scope,'weighted_sum','matmul',[weights,proj['v']],['B',h,'T',d],'Attention','context = torch.matmul')
        ct=op(attention_scope,'context_transpose','transpose',[ctx],['B','T',h,d],'Attention','context = context.transpose')
        cm=op(attention_scope,'context_merge','reshape',[ct],shp,'Attention','context = context.transpose')
        oi=linear(attention_scope+'.o_proj',H,'Attention')
        o=op(attention_scope,'o_proj','linear',[cm],shp,'Attention','return self.o_proj',oi)
        ao=op(attention_scope,'output','output',[o],shp,'Attention','return self.o_proj')
        b.bind(attention_scope,att,ai,ao)
        residual=op(scope,'residual1','add',[inp,att],shp,'DecoderBlock','x = x + attended')
        n2=param(path+'.norm2','RMSNorm',{'weight':[H]})
        norm2=op(scope,'norm2','rmsnorm',[residual],shp,'DecoderBlock','self.norm2',n2)
        mlp_scope=path+'.mlp'; mi=param(mlp_scope,'GatedMLP',{})
        mlp=op(scope,'mlp','mlp',[norm2],shp,'DecoderBlock','self.mlp',mi,mlp_scope)
        b.scope(mlp_scope,'Gated MLP','GatedMLP',scope,mlp)
        mx=op(mlp_scope,'x','input',[],shp,'GatedMLP')
        gp=param(mlp_scope+'.gate_proj','GatedMLP',{'weight':[I,H]},'torch.nn.Linear'); up=param(mlp_scope+'.up_proj','GatedMLP',{'weight':[I,H]},'torch.nn.Linear'); down=param(mlp_scope+'.down_proj','GatedMLP',{'weight':[H,I]},'torch.nn.Linear')
        g=op(mlp_scope,'gate_proj','linear',[mx],['B','T',I],'GatedMLP','gate =',gp)
        u=op(mlp_scope,'up_proj','linear',[mx],['B','T',I],'GatedMLP','up =',up)
        s=op(mlp_scope,'silu','silu',[g],['B','T',I],'GatedMLP','activated =')
        m=op(mlp_scope,'gated_product','mul',[s,u],['B','T',I],'GatedMLP','product =')
        z=op(mlp_scope,'down_proj','linear',[m],shp,'GatedMLP','return self.down_proj',down)
        mo=op(mlp_scope,'output','output',[z],shp,'GatedMLP','return self.down_proj')
        b.bind(mlp_scope,mlp,mx,mo)
        r2=op(scope,'residual2','add',[residual,mlp],shp,'DecoderBlock','return x + transformed')
        out=op(scope,'output','output',[r2],shp,'DecoderBlock','return x + transformed')
        b.bind(scope,owner,inp,out); x=owner
    b.doc['views'].append(dict(id='repeat:blocks',instances=blocks,relation='同结构、相同配置、独立参数；已逐层校验；全部实例保留',checked=True))
    norm=param('final_norm','RMSNorm',{'weight':[H]})
    x=op(model,'final_norm','rmsnorm',[x],shp,'MiniDecoder','self.final_norm',norm)
    head=param('lm_head','MiniDecoder',{'weight':[V,H]},'torch.nn.Linear')
    x=op(model,'lm_head','linear',[x],['B','T',V],'MiniDecoder','self.lm_head',head)
    op(model,'logits','output',[x],['B','T',V],'MiniDecoder','return self.lm_head')
    b.doc['limitations'].append(dict(reason='教学适配器：完整 AST 指纹匹配；分头链拆为源码子运算。无 RoPE、KV cache、性能测量。未运行目标源码。',sourceRef=b.symbols['MiniDecoder'],scope=model))
    for key,value in c.items():
        ev=b.evidence('config:'+key,'/snapshot/config/'+key,b.symbols['MiniDecoder'],f'配置 {key}={value}','config')
        b.doc['claims'].append(dict(id='claim:'+key,target='/snapshot/config/'+key,text=f'{key}={value}',evidence=[ev]))
    return b.finish(True)


# Restricted arithmetic interpreter. Never eval/import target code.
def constant(n,c):
    if isinstance(n,ast.Constant) and type(n.value) in (int,bool): return n.value
    if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id in ('c','config') and isinstance(n.slice,ast.Constant): return c[n.slice.value]
    if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.FloorDiv)):
        a,z=constant(n.left,c),constant(n.right,c)
        if type(a)!=int or type(z)!=int: raise ValueError('不是整数表达式')
        result={ast.Add:lambda:a+z,ast.Sub:lambda:a-z,ast.Mult:lambda:a*z,ast.FloorDiv:lambda:a//z}[type(n.op)]()
        if abs(result)>1_000_000: raise ValueError('表达式过大')
        return result
    raise ValueError('非受限常量表达式')


def generic(b, entry, c):
    from .generic import analyze_generic
    return analyze_generic(b, entry, c)


def analyze(source, entry, config, root):
    source=safe_path(source,root); cfg=safe_path(config,root)
    c=json.loads(cfg.read_text()); text=source.read_text(encoding='utf-8')
    if not isinstance(c,dict): raise ValueError('配置必须是对象')
    b=Builder(text,source.relative_to(Path(root).resolve()).as_posix(),entry,c)
    if entry not in b.classes: raise ValueError(f'未找到入口类 {entry}')
    canonical=files('model_atlas').joinpath('resources/teaching.ast.sha256').read_text().strip()
    fingerprint=digest(ast.dump(b.tree,include_attributes=False))
    if entry=='MiniDecoder' and fingerprint==canonical: return teaching(b,c)
    if entry=='MiniDecoder':
        b.doc['limitations'].append(dict(reason='教学适配器 AST 失配，降级通用分析；不复用旧结构',sourceRef=b.symbols[entry],scope='model'))
    return generic(b,entry,c)
