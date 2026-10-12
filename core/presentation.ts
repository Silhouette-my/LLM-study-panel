import type {Architecture,Node,Shape} from './types';
import type {VisibleGraph,VisibleEdge} from './graph';

export function shapeLabel(shape:Shape):string {
 if(shape.length===1&&shape[0]===null)return '形状未确定';
 if(!shape.length)return '标量';
 return `[${shape.map(d=>d===null?'?':d).join(', ')}]`;
}
export function edgeLabel(shape:string):string {
 try {const dims=JSON.parse(shape);return Array.isArray(dims)?(dims.includes(null)?'':shapeLabel(dims)):shape;}catch{return '';}
}
const roles:Record<string,string>={add:'相加',sub:'相减',mul:'相乘',div:'相除',cast:'类型转换',detach:'停止梯度',index:'索引',gather:'按索引提取',stack:'堆叠特征',cat:'拼接',softmax:'Softmax',masked_fill:'应用掩码',squeeze:'移除单维',field:'读取属性',log:'取对数'};
export function shortLabel(n:Node):string {
 if(n.childScope||n.instance)return n.label.replace(/^self\./,'');
 if(n.role==='conditional_result')return n.label;
 if(n.label.endsWith('（内部未展开）'))return n.label.replace('（内部未展开）','').slice(0,30)+'\n条件区域 · 未展开';
 if(roles[n.role])return roles[n.role];
 return n.label.length>35?n.label.slice(0,32)+'…':n.label;
}
export type PresentationGraph=VisibleGraph&{members:Record<string,string[]>;internalEdgeIds:string[]};
// Display-only contractions. A helper is contracted only into its sole successor;
// no bypass edges are invented, and every original edge remains auditable.
export function overview(g:VisibleGraph):PresentationGraph {
 const representative=new Map(g.nodes.map(n=>[n.id,n.id]));
 const root=(id:string):string=>{let p=id;while(representative.get(p)!==p)p=representative.get(p)!;return p;};
 const keep=(n:Node)=>Boolean(n.instance||n.childScope||['input','output','gather','stack','cat','softmax'].includes(n.role));
 for(const n of [...g.nodes].reverse()) {
  if(keep(n))continue;
  const targets=new Set(g.edges.filter(e=>e.source===n.id).map(e=>root(e.target)));
  if(targets.size===1){const target=[...targets][0];if(target!==root(n.id))representative.set(root(n.id),target);}
 }
 // Inputs have no incoming edges; combine only within their actual scope.
 const inputs=new Map<string,string>();
 for(const n of g.nodes.filter(n=>n.role==='input')) {
  if(g.edges.some(e=>e.target===n.id))continue;
  const first=inputs.get(n.scope);if(first)representative.set(n.id,first);else inputs.set(n.scope,n.id);
 }
 const members:Record<string,string[]>={};
 for(const n of g.nodes)(members[root(n.id)]??=[]).push(n.id);
 const nodes=g.nodes.filter(n=>root(n.id)===n.id);
 const internalEdgeIds:string[]=[],edges=new Map<string,VisibleEdge>();
 for(const e of g.edges){
  const source=root(e.source),target=root(e.target);
  if(source===target){internalEdgeIds.push(...e.originalEdgeIds);continue;}
  const key=JSON.stringify([source,target]),old=edges.get(key);
  if(old){old.originalEdgeIds.push(...e.originalEdgeIds);old.tensorIds.push(...e.tensorIds);old.portPairs.push(...e.portPairs);old.conditions=[...new Set([...old.conditions,...e.conditions])];old.count+=e.count;if(old.shape!==e.shape)old.shape='多种形状';}
  else edges.set(key,{...e,id:'overview:'+e.id,source,target,originalEdgeIds:[...e.originalEdgeIds],tensorIds:[...e.tensorIds],portPairs:[...e.portPairs],conditions:[...e.conditions]});
 }
 return {nodes,edges:[...edges.values()],members,internalEdgeIds};
}
export function present(a:Architecture,g:VisibleGraph,detail:boolean):PresentationGraph {
 if(detail||!a.limitations.some(l=>l.reason.includes('通用 AST')))return {...g,members:Object.fromEntries(g.nodes.map(n=>[n.id,[n.id]])),internalEdgeIds:[]};
 return overview(g);
}
