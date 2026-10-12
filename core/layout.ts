import ELK,{type ElkNode} from 'elkjs/lib/elk.bundled.js';
import type {VisibleGraph} from './graph';
import type {TeachingGroup} from './scene';
export type Point={x:number;y:number};
export type DiagramLayout={positions:Record<string,Point>;routes:Record<string,Point[]>;groups:Record<string,{x:number;y:number;width:number;height:number}>};
const elk=new ELK();
export const NODE_WIDTH=200,NODE_HEIGHT=76;
export async function layoutGraph(g:VisibleGraph,groups:TeachingGroup[]=[]):Promise<DiagramLayout>{
 const leaf=(id:string)=>({id,width:NODE_WIDTH,height:NODE_HEIGHT});
 const grouped=new Set(groups.flatMap(g=>g.visibleNodeIds));
 const children:ElkNode[]=groups.length?[
  ...groups.map(group=>({id:group.id,layoutOptions:{'elk.padding':'[top=88,left=32,bottom=32,right=32]'},children:group.visibleNodeIds.map(leaf)})),
  ...g.nodes.filter(n=>!grouped.has(n.id)).map(n=>leaf(n.id)),
 ]:g.nodes.map(n=>leaf(n.id));
 const result:ElkNode=await elk.layout({id:'root',layoutOptions:{
  'elk.algorithm':'layered','elk.direction':'DOWN','elk.edgeRouting':'ORTHOGONAL',
  'elk.hierarchyHandling':'INCLUDE_CHILDREN',
  'elk.spacing.nodeNode':'32','elk.layered.spacing.nodeNodeBetweenLayers':'34',
  'elk.layered.nodePlacement.strategy':'BRANDES_KOEPF',
  'elk.layered.nodePlacement.bk.fixedAlignment':'BALANCED',
  'elk.layered.crossingMinimization.strategy':'LAYER_SWEEP',
 },children,
 edges:g.edges.map(e=>({id:e.id,sources:[e.source],targets:[e.target]}))});
 const positions:Record<string,Point>={},boxes:DiagramLayout['groups']={};
 const visit=(node:ElkNode,ox=0,oy=0)=>{
  const x=ox+(node.x??0),y=oy+(node.y??0);
  if(node.children?.length){boxes[node.id]={x:x+(node.width??0)/2,y:y+(node.height??0)/2,width:node.width??0,height:node.height??0};node.children.forEach(n=>visit(n,x,y));}
  else positions[node.id]={x:x+NODE_WIDTH/2,y:y+NODE_HEIGHT/2};
 };
 result.children?.forEach(n=>visit(n));
 const routes:Record<string,Point[]>={};
 for(const e of result.edges??[]){
  if(e.sections?.length!==1)throw Error('布局缺少单一路由: '+e.id);
  const section=e.sections[0],container=boxes[e.container??''];
  const ox=container?container.x-container.width/2:0,oy=container?container.y-container.height/2:0;
  routes[e.id]=[section.startPoint,...(section.bendPoints??[]),section.endPoint].map(p=>({x:p.x+ox,y:p.y+oy}));
 }
 return {positions,routes,groups:boxes};
}
// Cytoscape segments use a source→target basis. Retain ELK's exact ports and
// waypoints; merely changing curve-style would discard its obstacle routing.
export function segmentStyle(points:Point[],source:Point,target:Point){
 const dx=target.x-source.x,dy=target.y-source.y,length2=dx*dx+dy*dy,length=Math.sqrt(length2);
 if(!length)throw Error('重合端点不能路由');
 const first=points[0],last=points.at(-1)!,bends=points.slice(1,-1);
 return {sourceEndpoint:`${first.x-source.x}px ${first.y-source.y}px`,targetEndpoint:`${last.x-target.x}px ${last.y-target.y}px`,
  weights:bends.map(p=>((p.x-source.x)*dx+(p.y-source.y)*dy)/length2),
  distances:bends.map(p=>((p.y-source.y)*dx-(p.x-source.x)*dy)/length)};
}
export function routeViolations(g:VisibleGraph,layout:DiagramLayout):string[]{
 const errors:string[]=[];
 for(const e of g.edges){
  const points=layout.routes[e.id];if(!points){errors.push('missing:'+e.id);continue;}
  for(const [point,id] of [[points[0],e.source],[points.at(-1)!,e.target]] as const){
   const p=layout.positions[id],dx=Math.abs(point.x-p.x),dy=Math.abs(point.y-p.y);
   if(dx>NODE_WIDTH/2+.01||dy>NODE_HEIGHT/2+.01||Math.abs(dx-NODE_WIDTH/2)>.01&&Math.abs(dy-NODE_HEIGHT/2)>.01)errors.push('detached-port:'+e.id+':'+id);
  }
  for(let i=1;i<points.length;i++){
   const a=points[i-1],b=points[i];
   if(Math.abs(a.x-b.x)>.01&&Math.abs(a.y-b.y)>.01)errors.push('diagonal:'+e.id);
   for(const n of g.nodes){
    if(n.id===e.source||n.id===e.target)continue;
    const p=layout.positions[n.id],left=p.x-NODE_WIDTH/2,right=p.x+NODE_WIDTH/2,top=p.y-NODE_HEIGHT/2,bottom=p.y+NODE_HEIGHT/2;
    if(Math.abs(a.x-b.x)<.01&&a.x>left+.01&&a.x<right-.01&&Math.max(a.y,b.y)>top+.01&&Math.min(a.y,b.y)<bottom-.01)errors.push('through-node:'+e.id+':'+n.id);
    if(Math.abs(a.y-b.y)<.01&&a.y>top+.01&&a.y<bottom-.01&&Math.max(a.x,b.x)>left+.01&&Math.min(a.x,b.x)<right-.01)errors.push('through-node:'+e.id+':'+n.id);
   }
  }
 }
 return errors;
}
