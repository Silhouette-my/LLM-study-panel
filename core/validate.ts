import type {Architecture,Bundle,Comparison,Session} from './types';
import validators from '../assets/validators.cjs';
export const MAX_BYTES=12_000_000;
export function parse(text:string):Architecture|Comparison|Session {
 if(new TextEncoder().encode(text).length>MAX_BYTES)throw Error('文件超过 12 MB 限制');
 return validate(JSON.parse(text));
}
export function validate(value:unknown):Architecture|Comparison|Session {
 const d=value as any;
 if(!d || !['architecture','comparison','session'].includes(d.kind))throw Error('未知文档 kind');
 const check=(validators as any)[d.kind];
 if(!check(d))throw Error('Schema 校验失败：'+JSON.stringify(check.errors?.slice(0,2)));
 if(d.kind==='architecture')semantic(d);
 if(d.kind==='comparison'){
  if(new Set(d.matches.map((m:any)=>m.id)).size!==d.matches.length)throw Error('重复匹配 ID');
  for(const m of d.matches)if(!m.left.length||!m.right.length)throw Error('匹配两侧不能为空');
  for(const m of d.matches)for(const side of ['left','right'])if(new Set(m[side]).size!==m[side].length)throw Error('匹配组重复节点');
  for(const diff of d.differences)if(diff.match&&!d.matches.some((m:any)=>m.id===diff.match))throw Error('差异引用未知匹配组');
 }
 return d;
}
function semantic(a:Architecture){
 if(a.nodes.length>3000)throw Error('图规模超过 3000 节点');
 const tables=new Map<string,Map<string,any>>();
 for(const k of ['definitions','instances','parameters','scopes','nodes','ports','edges','tensors','sourceRefs','evidence','claims','explanations','views'] as const){const values=a[k];const m=new Map(values.map(x=>[x.id,x]));if(m.size!==values.length)throw Error('重复 ID: '+k);tables.set(k,m);}
 const get=(k:string,id:string)=>{const item=tables.get(k)!.get(id);if(!item)throw Error(`悬空引用 ${k}: ${id}`);return item;};
 const roots=a.scopes.filter(s=>s.parent===null);if(roots.length!==1||roots[0].id!=='model'||roots[0].owner!==null||!a.nodes.length)throw Error('必须包含唯一 model 根作用域和非空调用图');
 for(const d of a.definitions)get('sourceRefs',d.sourceRef);
 for(const v of a.views)for(const i of v.instances)get('instances',i);
 for(const l of a.limitations){if(l.sourceRef)get('sourceRefs',l.sourceRef);if(l.scope)get('scopes',l.scope);}
 for(const n of a.nodes){get('scopes',n.scope);get('sourceRefs',n.sourceRef);get('explanations',n.explanation);if(n.instance)get('instances',n.instance);if(n.childScope){const s=get('scopes',n.childScope);if(s.owner!==n.id||s.parent!==n.scope)throw Error('子作用域归属错误');}}
 for(const p of a.ports){get('nodes',p.node);get('tensors',p.tensor);}
 for(const t of a.tensors){const p=get('ports',t.producer);if(p.tensor!==t.id||p.direction!=='out')throw Error('生产者错误');for(const c of t.consumers){const q=get('ports',c);if(q.tensor!==t.id||q.direction!=='in')throw Error('消费者错误');}get('evidence',t.evidence);if(t.shape.includes(null)&&!t.unknownReason)throw Error('未知形状缺少原因');}
 for(const e of a.edges){const s=get('ports',e.source),t=get('ports',e.target);if(s.direction!=='out'||t.direction!=='in'||s.tensor!==e.tensor||t.tensor!==e.tensor)throw Error('边端口错误');for(const p of [s,t])if(get('nodes',p.node).scope!==e.scope)throw Error('跨作用域边');}
 for(const s of a.scopes){get('sourceRefs',s.sourceRef);let cursor=s;const seen=new Set([s.id]);while(cursor.parent){cursor=get('scopes',cursor.parent);if(seen.has(cursor.id))throw Error('作用域环');seen.add(cursor.id);}for(const b of s.bindings){const p=get('ports',b.parentPort),q=get('ports',b.childPort);if(p.node!==s.owner||get('nodes',q.node).scope!==s.id||p.direction===q.direction)throw Error('绑定归属/方向错误');if(JSON.stringify(get('tensors',p.tensor).shape)!==JSON.stringify(get('tensors',q.tensor).shape))throw Error('绑定形状错误');}if(s.owner){if(get('nodes',s.owner).childScope!==s.id)throw Error('owner 反向引用错误');const ps=a.ports.filter(p=>p.node===s.owner).map(p=>p.id).sort(),bs=s.bindings.map(b=>b.parentPort).sort();if(JSON.stringify(ps)!==JSON.stringify(bs))throw Error('绑定不完整');}}
 for(const p of a.parameters){if(p.count!==p.shape.reduce((s,v)=>s*v,1))throw Error('参数 shape/count 错误');for(const id of p.instances)get('instances',id);get('evidence',p.evidence);if(p.shared!==(p.instances.length>1))throw Error('共享标记错误');}
 for(const i of a.instances){if(i.definition)get('definitions',i.definition);for(const id of i.parameterIds)if(!get('parameters',id).instances.includes(i.id))throw Error('参数归属错误');}
 for(const e of a.evidence)for(const r of e.sourceRefs)get('sourceRefs',r);
 for(const x of [...a.explanations,...a.claims])for(const e of x.evidence)get('evidence',e);
 if(a.snapshot.parameterCount!==null&&a.snapshot.parameterCount!==a.parameters.reduce((s,p)=>s+p.count,0))throw Error('参数总数错误');
}
export function validateComparison(c:Comparison,left:Architecture,right:Architecture){
 validate(c);if(c.leftSnapshot!==left.snapshot.id||c.rightSnapshot!==right.snapshot.id)throw Error('对比快照不匹配');
 for(const m of c.matches){for(const id of m.left)if(!left.nodes.some(n=>n.id===id))throw Error('左匹配悬空');for(const id of m.right)if(!right.nodes.some(n=>n.id===id))throw Error('右匹配悬空');}
}
export function validateBundle(b:Bundle){if(!b||!Array.isArray(b.architectures)||b.architectures.length<1||b.architectures.length>2)throw Error('需要 1–2 份架构');b.architectures.forEach(a=>{if(validate(a).kind!=='architecture')throw Error('需要架构');});if(b.comparison){if(b.architectures.length!==2)throw Error('对比需要两份架构');validateComparison(b.comparison,b.architectures[0],b.architectures[1]);}return b;}
export function associateNotes(s:Session,docs:Architecture[]):Session {
 validate(s);return {kind:'session',schemaVersion:'1.0',notes:s.notes.map(n=>({...n,association:docs.some(a=>a.snapshot.id===n.snapshot&&a.nodes.some(x=>x.id===n.anchor))?'exact':'pending'}))};
}
