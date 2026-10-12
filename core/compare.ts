import type {Architecture,Comparison,Difference,Match,Node} from './types';
const output=(a:Architecture,n:Node)=>a.tensors.filter(t=>a.ports.some(p=>p.id===t.producer&&p.node===n.id)).map(t=>t.shape);
const count=(a:Architecture,ns:Node[])=>{const ids=new Set(ns.flatMap(n=>a.instances.find(i=>i.id===n.instance)?.parameterIds??[]));return a.parameters.filter(p=>ids.has(p.id)).reduce((s,p)=>s+p.count,0);};
const signature=(a:Architecture,n:Node)=>JSON.stringify([n.role,a.scopes.find(s=>s.id===n.scope)?.parent===null?'root':'child',a.edges.filter(e=>a.ports.find(p=>p.id===e.target)?.node===n.id).length,a.edges.filter(e=>a.ports.find(p=>p.id===e.source)?.node===n.id).length,!!n.childScope]);
const equal=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
export function compare(left:Architecture,right:Architecture, matches?:Match[]):Comparison {
 if(!matches){
  matches=[];const used=new Set<string>();
  for(const n of left.nodes){
   const exact=right.nodes.find(r=>r.id===n.id&&r.role===n.role&&!used.has(r.id));
   const candidates=right.nodes.filter(r=>!used.has(r.id)&&signature(left,n)===signature(right,r));
   const r=exact??(candidates.length===1?candidates[0]:null);
   if(r){used.add(r.id);matches.push({id:'match:'+n.id,left:[n.id],right:[r.id],status:'suggested',origin:'rule',reason:exact?'作用域位置、角色和静态调用结构对应；建议不是等价证明':'唯一角色/边界/连接候选；名称不同仍需人工核对'});}
  }
 }
 for(const m of matches){for(const id of m.left)if(!left.nodes.some(n=>n.id===id))throw Error('左侧匹配引用不存在');for(const id of m.right)if(!right.nodes.some(n=>n.id===id))throw Error('右侧匹配引用不存在');}
 const differences:Difference[]=[];
 const add=(type:Difference['type'],text:string,match:string|null,evidence:string[])=>differences.push({type,text,match,evidence});
 for(const key of new Set([...Object.keys(left.snapshot.config),...Object.keys(right.snapshot.config)]))if(!equal(left.snapshot.config[key],right.snapshot.config[key]))add('configuration',`${key}: ${JSON.stringify(left.snapshot.config[key])} → ${JSON.stringify(right.snapshot.config[key])}`,null,[`left:/snapshot/config/${key}`,`right:/snapshot/config/${key}`]);
 for(const m of matches.filter(m=>m.status!=='rejected')){
  const ls=m.left.map(id=>left.nodes.find(n=>n.id===id)!),rs=m.right.map(id=>right.nodes.find(n=>n.id===id)!);
  const evidence=[...ls.map(n=>'left:'+n.sourceRef),...rs.map(n=>'right:'+n.sourceRef)];
  if(ls.some(n=>n.opaque)||rs.some(n=>n.opaque)){add('unknown','包含 opaque 节点，不能证明计算等价',m.id,evidence);continue;}
  if(ls.length!==1||rs.length!==1){add('unknown','人工分组对应已保存；多对多的计算等价需要审查',m.id,evidence);}
  if(!equal(ls.flatMap(n=>output(left,n)),rs.flatMap(n=>output(right,n))))add('shape',`${ls.map(n=>n.label).join('+')}: ${JSON.stringify(ls.flatMap(n=>output(left,n)))} → ${JSON.stringify(rs.flatMap(n=>output(right,n)))}`,m.id,evidence);
  const lp=count(left,ls),rp=count(right,rs);if(lp!==rp)add('parameters',`注册独立参数（本节点直属模块）：${lp} → ${rp}，Δ=${rp-lp}`,m.id,evidence);
  const shared=(a:Architecture,ns:Node[])=>ns.map(n=>a.instances.find(i=>i.id===n.instance)?.parameterIds.map(id=>a.parameters.find(p=>p.id===id)?.shared)??[]);
  if(!equal(shared(left,ls),shared(right,rs)))add('sharing','参数共享关系发生变化',m.id,evidence);
  if(!equal(ls.map(n=>signature(left,n)),rs.map(n=>signature(right,n))))add('topology','角色、边界或连接数量发生变化',m.id,evidence);
  if(ls.length===1&&rs.length===1&&ls[0].label!==rs[0].label)add('implementation','名称或实现组织改变；不据此认定计算机制改变',m.id,evidence);
 }
 const accepted=matches.filter(m=>m.status!=='rejected');
 const coveredLeft=new Set(accepted.flatMap(m=>m.left)),coveredRight=new Set(accepted.flatMap(m=>m.right));
 const unmatchedLeft=left.nodes.filter(n=>!coveredLeft.has(n.id)).map(n=>n.id),unmatchedRight=right.nodes.filter(n=>!coveredRight.has(n.id)).map(n=>n.id);
 if(unmatchedLeft.length||unmatchedRight.length)add('unknown',`未匹配：左 ${unmatchedLeft.length} / 右 ${unmatchedRight.length}；不强行判定新增删除`,null,[]);
 // Compare actual edge connectivity after applying accepted/suggested groups.
 const groupMap=(side:'left'|'right')=>new Map(accepted.flatMap(m=>m[side].map(id=>[id,m.id] as const)));
 const topology=(a:Architecture,map:Map<string,string>)=>a.edges.map(e=>{const s=a.ports.find(p=>p.id===e.source)!.node,t=a.ports.find(p=>p.id===e.target)!.node;return map.has(s)&&map.has(t)?JSON.stringify([map.get(s),map.get(t)]):null;}).filter(x=>x!==null).sort();
 if(!equal(topology(left,groupMap('left')),topology(right,groupMap('right'))))add('topology','已匹配模块之间的数据依赖发生变化',null,['left:/edges','right:/edges']);
 const lc=left.snapshot.parameterCount,rc=right.snapshot.parameterCount;
 const cache=(a:Architecture)=>{const c=a.snapshot.config;const keys=['num_layers','num_key_value_heads','head_dim'];if(!keys.every(k=>typeof c[k]==='number'))return null;return 2*Number(c.num_layers)*2*4*Number(c.num_key_value_heads)*Number(c.head_dim)*4;};
 const lcache=cache(left),rcache=cache(right);
 const projection=(a:Architecture)=>{const c=a.snapshot.config;const H=Number(c.hidden_size),h=Number(c.num_attention_heads),kv=Number(c.num_key_value_heads),d=Number(c.head_dim);if(![H,h,kv,d].every(Number.isFinite))return null;return {qOutput:h*d,kvOutput:kv*d,kvWeightParametersPerLayer:2*H*kv*d,explanation:`Q 输出 heads×head_dim=${h}×${d}=${h*d}；K/V 各输出 kv_heads×head_dim=${kv}×${d}=${kv*d}；无 bias 时 K/V 合计参数 2×hidden_size×kv_heads×head_dim=${2*H*kv*d}。静态推导，未测量。`,evidence:['/snapshot/config/num_key_value_heads','/snapshot/config/hidden_size','/snapshot/config/head_dim','源码 Attention.__init__/forward']};};
 const lp=projection(left),rp=projection(right);

 return {kind:'comparison',schemaVersion:'1.0',leftSnapshot:left.snapshot.id,rightSnapshot:right.snapshot.id,matches,differences,summary:{projectionEffects:[lp,rp],kvProjectionWeightDeltaPerLayer:lp&&rp?rp.kvWeightParametersPerLayer-lp.kvWeightParametersPerLayer:null,unmatchedLeft,unmatchedRight,parameterCounts:[lc,rc],parameterDelta:lc!==null&&rc!==null?rc-lc:null,theoreticalCache:{formula:'2 × layers × B × T_cache × kv_heads × head_dim × bytes_per_element',assumptions:'理论估算，未测量；未复制 KV 存储；B=2，T_cache=4，float32=4 bytes；示例未实现 cache',bytes:[lcache,rcache],ratio:lcache&&rcache?rcache/lcache:null}},limitations:['自动对应是建议，不是数学等价证明。','无真实显存、速度或效果测量；未知统计口径不作数值比较。']};
}
export function correct(left:Architecture,right:Architecture,c:Comparison,ids:{left:string[],right:string[]}):Comparison {
 if(!ids.left.length||!ids.right.length)throw Error('请选择两侧节点');
 const matches=c.matches.map(m=>m.left.some(id=>ids.left.includes(id))||m.right.some(id=>ids.right.includes(id))?{...m,status:'rejected' as const}:m);
 matches.push({id:'manual:'+JSON.stringify([ids.left,ids.right])+':'+matches.length,...ids,status:'accepted',origin:'manual',reason:'用户指定；仅改变对应关系，不证明等价'});
 return compare(left,right,matches);
}
