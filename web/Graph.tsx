import React,{useEffect,useMemo,useRef,useState} from 'react';
import cytoscape from 'cytoscape';
import type {Architecture,Node} from '../core/types';
import {project,dependencies,teachingLayers} from '../core/graph';
import {present,shortLabel,edgeLabel} from '../core/presentation';
import {layoutGraph,segmentStyle,NODE_WIDTH,NODE_HEIGHT,type DiagramLayout} from '../core/layout';
import {teachingGroups} from '../core/scene';
import {sketchNode,sketchLabel,nodeTone,palette} from './sketch';
export type View={detail:boolean;scope:string;expanded:string[];selected:string|null;edge:string|null;step:number;direction:'forward'|'backward'|null;teaching?:boolean;showShapes?:boolean};
export const initialView=():View=>({detail:false,scope:'model',expanded:[],selected:null,edge:null,step:-1,direction:null,teaching:false,showShapes:false});
const layoutCache=new Map<string,DiagramLayout>();
const cameraCache=new Map<string,{zoom:number;pan:{x:number;y:number}}>;
type Props={a:Architecture;v:View;side:number;onChange:(p:Partial<View>)=>void;onEnter?:(n:Node)=>void;onSide?:(n:Node)=>void;differences?:Record<string,string>;referenceNode?:string;onReferencePoint?:(p:{x:number;y:number})=>void};
export function Graph({a,v,side,onChange,onEnter,onSide,differences={},referenceNode,onReferencePoint}:Props){
 const box=useRef<HTMLDivElement>(null),cyRef=useRef<cytoscape.Core|null>(null),state=useRef(v);
 state.current=v;const referenceCallback=useRef(onReferencePoint);referenceCallback.current=onReferencePoint;
 const lastFrame=useRef<{scope:string;zoom:number;pan:{x:number;y:number};anchor?:{id:string;x:number;y:number}}|null>(null);
 const [layoutError,setLayoutError]=useState('');
 const g=useMemo(()=>present(a,project(a,v.scope,new Set(v.expanded)),v.detail||v.expanded.length>0),[a,v.scope,v.expanded,v.detail]);
 const groups=useMemo(()=>teachingGroups(a,g,v.scope),[a,g,v.scope]);
 const key=JSON.stringify([a.snapshot.id,side,v.scope,v.detail,[...v.expanded].sort()]);
 const selected=a.nodes.find(n=>n.id===v.selected);
 useEffect(()=>{
  let cancelled=false;setLayoutError('');box.current!.dataset.layoutReady='false';const started=performance.now();
  const cy=cytoscape({container:box.current!,elements:[],autoungrabify:true,style:[
   {selector:'node',style:{label:'data(label)','background-color':palette.canvas,'background-image':'data(texture)','background-fit':'contain','border-width':.6,'border-color':'data(tone)',color:'#ececf1',shape:'round-rectangle','corner-radius':'4px',width:NODE_WIDTH,height:NODE_HEIGHT,'text-wrap':'wrap','text-overflow-wrap':'anywhere','text-max-width':'180px','font-size':16,'text-valign':'center','text-halign':'center','z-index':2,'z-index-compare':'manual'}},
   {selector:'node[uiOnly]',style:{'background-image':'none','background-opacity':.015,'background-color':palette.group,'border-width':1.6,'border-color':palette.group,'border-style':'dashed','border-dash-pattern':[10,7],width:'data(width)',height:'data(height)',label:'data(label)',color:palette.group,'text-valign':'top','text-halign':'left','text-justification':'left','text-margin-y':76,'text-margin-x':(n:cytoscape.NodeSingular)=>Number(n.data('titleOffset')),'text-max-width':'data(labelWidth)','font-size':22,'font-weight':500,'z-index':0,events:'no'}},
   {selector:'edge',style:{width:1.5,'line-color':palette.edge,'target-arrow-color':palette.edge,'target-arrow-shape':'triangle','curve-style':'taxi','taxi-direction':'downward','taxi-turn':20,'edge-distances':'node-position',label:'','font-size':12,color:'#ececf1','text-background-color':palette.canvas,'text-background-opacity':1,'text-background-padding':'4px','z-index':1,'z-index-compare':'manual'}},
   {selector:'edge.chosen',style:{width:2.8,'line-color':'#f4f2ff','target-arrow-color':'#f4f2ff'}},
   {selector:'node.chosen',style:{'border-width':2.4,'border-color':'#f4f2ff'}},
   {selector:'.lit',style:{'border-width':2,'border-color':'#f4f2ff','line-color':'#f4f2ff','target-arrow-color':'#f4f2ff'}},
   {selector:'.dim',style:{opacity:.55}},
  ],minZoom:.15,maxZoom:2.5,wheelSensitivity:.18});cyRef.current=cy;
  cy.add([...groups.map(group=>({data:{id:group.id,uiOnly:1,sourceNodeIds:group.sourceNodeIds,sourceRefs:group.sourceRefs,snapshot:group.snapshot,role:'teaching-group',label:group.label+'\n教学分组',width:10,height:10,labelWidth:200,titleOffset:120}})),...g.nodes.map(n=>({data:{id:n.id,role:n.role,sourceNodeIds:g.members[n.id],snapshot:a.snapshot.id,tone:nodeTone(n),texture:sketchNode(n.id,NODE_WIDTH,NODE_HEIGHT,nodeTone(n)),label:sketchLabel(n,g.members[n.id].length),...(n.childScope?{child:1}:{})}})),...g.edges.map(e=>({data:{id:e.id,source:e.source,target:e.target,label:'',shape:edgeLabel(e.shape),originalEdgeIds:e.originalEdgeIds,tensorIds:e.tensorIds,portPairs:e.portPairs,conditions:e.conditions}}))]);
  cy.on('tap','node',ev=>{if(!ev.target.data('uiOnly'))onChange({selected:ev.target.id(),edge:null,direction:null});});
  cy.on('dbltap','node',ev=>{const n=a.nodes.find(n=>n.id===ev.target.id());if(n?.childScope)onEnter?.(n);});
  cy.on('tap','edge',ev=>onChange({edge:ev.target.id(),selected:null,direction:null}));
  const frame=()=>{
   const n=cy.nodes('.chosen').filter(n=>!n.data('uiOnly')).first() as cytoscape.NodeSingular;
   const anchor=n?.length?{id:n.id(),...n.position()}:undefined;
   return {scope:v.scope,zoom:cy.zoom(),pan:{...cy.pan()},anchor};
  };
  const resize=new ResizeObserver(()=>{
   if(cancelled||!cy.nodes().length)return;
   cy.resize();if(box.current?.dataset.layoutReady!=='true')return;const id=state.current.selected;if(!id)return;
   const n=cy.getElementById(id);if(!n.length)return;
   const p=n.renderedPosition(),pad=Math.min(cy.width()/2-12,Math.max(70,NODE_WIDTH*cy.zoom()/2+16));
   const dx=p.x<pad?pad-p.x:p.x>cy.width()-pad?cy.width()-pad-p.x:0;
   const dy=p.y<pad?pad-p.y:p.y>cy.height()-pad?cy.height()-pad-p.y:0;
   let shiftX=dx,shiftY=dy;const group=cy.nodes().filter(g=>g.data('uiOnly')&&g.data('sourceNodeIds')?.includes(id)).first();if(group.length){const b=group.renderedBoundingBox();if(b.w<cy.width()-32)shiftX=b.x1<16?16-b.x1:b.x2>cy.width()-16?cy.width()-16-b.x2:0;if(b.h<cy.height()-32)shiftY=b.y1<16?16-b.y1:b.y2>cy.height()-16?cy.height()-16-b.y2:0;}if(shiftX||shiftY)cy.panBy({x:shiftX,y:shiftY});
  });resize.observe(box.current!);
  const place=async()=>{
   let layout=layoutCache.get(key);if(!layout){layout=await layoutGraph(g,groups);layoutCache.set(key,layout);}
   if(cancelled)return;
   cy.batch(()=>{
    cy.nodes().filter(n=>!n.data('uiOnly')).positions(n=>layout!.positions[n.id()]);
    for(const group of groups){const bounds=layout.groups[group.id];cy.getElementById(group.id).data({width:bounds.width,height:bounds.height,labelWidth:bounds.width-40}).position({x:bounds.x,y:bounds.y});}
    cy.edges().forEach(e=>{
     const points=layout!.routes[e.id()],style=segmentStyle(points,layout!.positions[e.source().id()],layout!.positions[e.target().id()]);
     e.data('routePoints',points);e.style({'curve-style':style.weights.length?'round-segments':'straight','source-endpoint':style.sourceEndpoint,'target-endpoint':style.targetEndpoint,...(style.weights.length?{'segment-weights':style.weights,'segment-distances':style.distances,'segment-radii':6}:{})});
    });
   });
   const saved=cameraCache.get(key),previous=lastFrame.current;
   if(saved){cy.zoom(saved.zoom);cy.pan(saved.pan);}
   else if(previous?.scope===v.scope){
    cy.zoom(previous.zoom);cy.pan(previous.pan);
    if(previous.anchor){let next=layout.positions[previous.anchor.id];if(!next){const scope=a.nodes.find(n=>n.id===previous.anchor!.id)?.childScope;const boundary=g.nodes.find(n=>n.scope===scope&&n.role==='input');if(boundary)next=layout.positions[boundary.id];}if(next)cy.panBy({x:(previous.anchor.x-next.x)*previous.zoom,y:(previous.anchor.y-next.y)*previous.zoom});}
   }else cy.fit(undefined,48);
   const adjustTexture=()=>cy.nodes().filter(n=>!n.data('uiOnly')).style('background-image-opacity',cy.zoom()<.35?0:1);
   cy.on('zoom',adjustTexture);adjustTexture();
   if(!v.detail)cy.nodes().filter(n=>!n.data('uiOnly')).forEach(n=>{let size=Math.min(30,14/cy.zoom());const lines=String(n.data('label')).split('\n');const count=(s:number)=>lines.reduce((sum,line)=>sum+Math.max(1,Math.ceil([...line].reduce((w,c)=>w+(c.charCodeAt(0)>255?s:s*.56),0)/180)),0);while(size>16&&count(size)*size*1.15>NODE_HEIGHT-12)size--;n.style('font-size',size);});
   cy.nodes().filter(n=>Boolean(n.data('uiOnly'))).forEach(n=>{const size=Math.min(26,15/cy.zoom());n.style('font-size',size);const ctx=document.createElement('canvas').getContext('2d')!;ctx.font=`500 ${size}px ${String(n.style('font-family'))}`;const width=Math.max(...String(n.data('label')).split('\n').map(line=>ctx.measureText(line).width));n.data('titleOffset',Math.min(width,Number(n.data('labelWidth')))+16);});
   box.current!.dataset.layoutReady='true';cy.emit('layoutready');
   const metrics={snapshot:a.snapshot.id,scope:v.scope,nodes:g.nodes.length,edges:g.edges.length,groups:groups.length,layoutAndMountMs:performance.now()-started};
   (window as any).__atlasMetrics=[...((window as any).__atlasMetrics??[]),metrics];
  };place().catch(e=>{if(!cancelled){setLayoutError(String(e));console.error(e);}});
  return ()=>{cancelled=true;resize.disconnect();const f=frame();cameraCache.set(key,{zoom:f.zoom,pan:f.pan});lastFrame.current=f;cy.destroy();cyRef.current=null;};
 },[g,key,groups]);
 useEffect(()=>{
  const cy=cyRef.current;if(!cy||!referenceNode)return;
  const report=()=>{if(box.current?.dataset.layoutReady!=='true')return;const n=cy.getElementById(referenceNode);if(!n.length)return;const p=n.renderedPosition(),bounds=box.current.getBoundingClientRect();referenceCallback.current?.({x:bounds.left+p.x+NODE_WIDTH*cy.zoom()/2,y:bounds.top+p.y});};
  cy.on('pan zoom resize layoutready',report);report();return()=>{cy.off('pan zoom resize layoutready',report);};
 },[referenceNode,key,g]);
 useEffect(()=>{
  const cy=cyRef.current;if(!cy)return;cy.elements().removeClass('chosen lit dim');
  const representative=v.selected?Object.keys(g.members).find(id=>g.members[id].includes(v.selected!)):null;
  if(representative)cy.getElementById(representative).addClass('chosen');if(v.edge)cy.getElementById(v.edge).addClass('chosen');
  let lit:Set<string>|null=null;if(v.step>=0){const layers=teachingLayers(g);lit=new Set(layers[Math.min(v.step,layers.length-1)]??[]);}if(v.direction&&representative)lit=dependencies(g,representative,v.direction);
  if(lit){cy.nodes().filter(n=>!n.data('uiOnly')).forEach(n=>{n.addClass(lit!.has(n.id())?'lit':'dim');});cy.edges().forEach(e=>{e.addClass(lit!.has(e.source().id())&&lit!.has(e.target().id())?'lit':'dim');});}
  cy.edges().forEach(e=>{e.style('label',v.showShapes||v.edge===e.id()?e.data('shape'):'');});
  cy.nodes().filter(n=>!n.data('uiOnly')).forEach(e=>{const n=a.nodes.find(n=>n.id===e.id())!;const suffix=differences[n.id]?'  '+differences[n.id]:'';e.data('label',sketchLabel(n,g.members[n.id].length)+suffix);});
 },[v.selected,v.edge,v.step,v.direction,v.showShapes,g,differences]);
 return <div className="graph-scene">
  {layoutError&&<div role="alert" className="error">布局失败：{layoutError}</div>}
  <div className="graph" ref={box} aria-label={`模型 ${side} 数据流图`}/>
  <div className="graph-tools" aria-label="画布工具">
   <button onClick={()=>cyRef.current?.fit(undefined,48)}>适配画布</button><button aria-label={`放大 ${side}`} onClick={()=>{const c=cyRef.current;if(c)c.zoom(Math.min(2.5,c.zoom()*1.2));}}>＋</button><button aria-label={`缩小 ${side}`} onClick={()=>{const c=cyRef.current;if(c)c.zoom(Math.max(.15,c.zoom()/1.2));}}>－</button>
   <button aria-pressed={!v.detail} onClick={()=>onChange({detail:false,step:-1,direction:null})}>主流程</button><button aria-pressed={v.detail} onClick={()=>onChange({detail:true,step:-1,direction:null})}>计算细节</button>
   {v.teaching&&<><button onClick={()=>onChange({step:(v.step+1)%teachingLayers(g).length,direction:null})}>教学下一步</button><button onClick={()=>onChange({step:-1,direction:null})}>清除高亮</button><span>依赖层 {v.step+1} · 非执行回放</span></>}
  </div>
  {selected&&<div className="selected-tools"><span>{shortLabel(selected)}</span>{selected.childScope?<><button onClick={()=>onEnter?.(selected)}>进入</button><button onClick={()=>onChange({expanded:v.expanded.includes(selected.id)?v.expanded.filter(id=>id!==selected.id):[...v.expanded,selected.id]})}>{v.expanded.includes(selected.id)?'− 折叠一级':'+ 展开一级'}</button><button onClick={()=>onSide?.(selected)}>旁侧查看</button></>:selected.opaque?<span>? 查看边界/源码</span>:null}</div>}
  <details className="node-list"><summary>节点与教学分组 · {g.nodes.length} 项</summary><div className="accessible-nodes" aria-label={`图节点 ${side}`}>{g.nodes.map(n=><button key={n.id} aria-pressed={v.selected===n.id} onClick={()=>onChange({selected:n.id,edge:null})}>{n.label}</button>)}</div><div className="group-list">{groups.map(group=><details key={group.id}><summary>{group.label} · 教学分组</summary><p>{group.basis}</p><small>原始节点 {group.sourceNodeIds.length} · 快照 {group.snapshot.slice(0,12)}</small></details>)}</div></details>
 </div>;
}
