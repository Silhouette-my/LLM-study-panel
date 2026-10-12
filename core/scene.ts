import type {Architecture} from './types';
import type {PresentationGraph} from './presentation';
import review from '../assets/laya-view-review.json';
export type TeachingGroup={id:string;label:string;kind:'teaching';snapshot:string;scope:string;visibleNodeIds:string[];sourceNodeIds:string[];sourceRefs:string[];basis:string;reviewer:string};
// Reviewed labels are scoped to an immutable source hash, never a class name alone.
export function teachingGroups(a:Architecture,g:PresentationGraph,scope:string):TeachingGroup[]{
 if(!g.nodes.length)return [];
 const verified=a.snapshot.sourceHash===review.sourceHash&&a.snapshot.model===review.model&&scope===review.scope;
 if(verified){
  const assigned=new Set<string>();
  const groups=review.groups.map(r=>{
   const visibleNodeIds=g.nodes.filter(n=>g.members[n.id].every(id=>r.sourceNodeIds.includes(id))).map(n=>n.id);
   visibleNodeIds.forEach(id=>assigned.add(id));
   return {id:'teaching:'+scope+':'+r.id,label:r.label,kind:'teaching' as const,snapshot:a.snapshot.id,scope,visibleNodeIds,sourceNodeIds:visibleNodeIds.flatMap(id=>g.members[id]),sourceRefs:r.sourceRefs.filter(id=>a.sourceRefs.some(s=>s.id===id)),basis:r.basis,reviewer:review.reviewer};
  }).filter(r=>r.visibleNodeIds.length);
  if(assigned.size===g.nodes.length)return groups;
 }
 // Structural grouping is explicit about its weaker basis. No task semantics
 // inferred from variable names; an unsupported model stays unsupported.
 const sourceNodeIds=g.nodes.flatMap(n=>g.members[n.id]);
 return [{id:'teaching:'+scope+':structure',label:a.scopes.find(s=>s.id===scope)?.label??scope,kind:'teaching',snapshot:a.snapshot.id,scope,visibleNodeIds:g.nodes.map(n=>n.id),sourceNodeIds,sourceRefs:[...new Set(sourceNodeIds.map(id=>a.nodes.find(n=>n.id===id)!.sourceRef))],basis:'按当前真实作用域整理的教学区域；不是新的模型模块，未选择动态执行路径。',reviewer:'structural view'}];
}
