import type {Architecture,Node} from './types';
export type VisibleEdge = {id:string;source:string;target:string;originalEdgeIds:string[];tensorIds:string[];portPairs:[string,string][];conditions:string[];shape:string;count:number};
export type VisibleGraph = {nodes:Node[];edges:VisibleEdge[]};
// Pure scope projection. Canonical data is never changed. Boundary nodes remain
// visible so fan-out/residual and multi-output bindings have explicit endpoints.
export function project(a:Architecture, scopeId:string, expanded:ReadonlySet<string>):VisibleGraph {
 const scopes=new Map(a.scopes.map(s=>[s.id,s]));
 if(!scopes.has(scopeId)) throw Error('未知作用域');
 const active=new Set([scopeId]); const removed=new Set<string>();
 const visit=(s:string,depth:number)=>{
  if(depth>64) throw Error('层级深度超限');
  for(const n of a.nodes.filter(n=>n.scope===s)) if(n.childScope && expanded.has(n.id)){
   if(active.has(n.childScope)) throw Error('层级环');
   active.add(n.childScope); removed.add(n.id); visit(n.childScope,depth+1);
  }
 }; visit(scopeId,0);
 const ports=new Map(a.ports.map(p=>[p.id,p]));
 const bindings=new Map(a.scopes.filter(s=>s.owner && removed.has(s.owner)).flatMap(s=>s.bindings.map(b=>[b.parentPort,b.childPort] as const)));
 const endpoint=(p:string):string=>{
  const seen=new Set<string>();
  while(bindings.has(p)){
   if(seen.has(p)||seen.size>128) throw Error('端口绑定环');
   seen.add(p);p=bindings.get(p)!;
  }
  const port=ports.get(p); if(!port) throw Error('悬空端口');
  if(removed.has(port.node)) throw Error('展开端口缺少绑定');
  return port.node;
 };
 const nodes=a.nodes.filter(n=>active.has(n.scope)&&!removed.has(n.id));
 const ids=new Set(nodes.map(n=>n.id));
 const groups=new Map<string,VisibleEdge>();
 const tensors=new Map(a.tensors.map(t=>[t.id,t]));
 for(const e of a.edges.filter(e=>active.has(e.scope))){
  const source=endpoint(e.source),target=endpoint(e.target);
  if(!ids.has(source)||!ids.has(target)) throw Error('可见边端点丢失');
  const key=JSON.stringify([source,target]);
  const shape=JSON.stringify(tensors.get(e.tensor)!.shape);
  const old=groups.get(key);
  if(old){old.originalEdgeIds.push(e.id);old.tensorIds.push(e.tensor);old.portPairs.push([e.source,e.target]);if(e.condition&&!old.conditions.includes(e.condition))old.conditions.push(e.condition);old.count++;if(old.shape!==shape)old.shape='多种形状，查看原始张量';}
  else groups.set(key,{id:'visible:'+e.id,source,target,originalEdgeIds:[e.id],tensorIds:[e.tensor],portPairs:[[e.source,e.target]],conditions:e.condition?[e.condition]:[],shape,count:1});
 }
 if(nodes.length>500) throw Error('当前视图超过 500 节点，请折叠或聚焦');
 return {nodes,edges:[...groups.values()]};
}
export function dependencies(g:VisibleGraph, selected:string, direction:'forward'|'backward'){
 const result=new Set([selected]); let changed=true;
 while(changed){changed=false;for(const e of g.edges){const from=direction==='forward'?e.source:e.target,to=direction==='forward'?e.target:e.source;if(result.has(from)&&!result.has(to)){result.add(to);changed=true;}}}
 return result;
}
// Layers express dependency levels; independent branches share a layer. This is
// a teaching view, not an observed runtime ordering.
export function teachingLayers(g:VisibleGraph):string[][] {
 const done=new Set<string>(), layers:string[][]=[];
 while(done.size<g.nodes.length){const layer=g.nodes.filter(n=>!done.has(n.id)&&g.edges.filter(e=>e.target===n.id).every(e=>done.has(e.source))).map(n=>n.id);if(!layer.length)throw Error('循环依赖，不能步进');layers.push(layer);for(const id of layer)done.add(id);}
 return layers;
}
