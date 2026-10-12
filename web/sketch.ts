import rough from 'roughjs';
import type {Node} from '../core/types';
import {shortLabel} from '../core/presentation';
const generator=rough.generator();
const cache=new Map<string,string>();
export const palette={canvas:'#171320',module:'#49a8d8',operation:'#a6c862',tensor:'#d8bc57',group:'#d26770',unknown:'#8b8e9e',edge:'#d5d5df'};
export function stableSeed(id:string):number{let n=2166136261;for(const ch of id)n=Math.imul(n^ch.charCodeAt(0),16777619);return (n>>>0)%2147483646+1;}
export function nodeTone(n:Node):string{return n.opaque?palette.unknown:n.childScope?palette.module:['input','output'].includes(n.role)?palette.tensor:palette.operation;}
export function sketchLabel(n:Node,members=1):string{
 let title=members>1&&n.role==='input'?`输入 · ${members} 项`:shortLabel(n).replace('\n条件区域 · 未展开','');
 const limit=n.opaque?22:30;if([...title].length>limit)title=[...title].slice(0,limit-1).join('')+'…';
 return title+(n.childScope?'  [+]':'')+(n.opaque?'\n? 未解析':'');
}
export function sketchNode(id:string,width:number,height:number,tone:string):string{
 const key=JSON.stringify([id,width,height,tone]);const old=cache.get(key);if(old)return old;
 const shape=generator.rectangle(4,4,width-8,height-8,{seed:stableSeed(id),roughness:.65,bowing:.35,stroke:tone,strokeWidth:1.4,fill:tone,fillStyle:'hachure',hachureAngle:-45,hachureGap:6,fillWeight:.55,disableMultiStroke:true});
 const paths=generator.toPaths(shape).map(p=>`<path d="${p.d}" stroke="${p.stroke}" stroke-width="${p.strokeWidth}" fill="${p.fill??'none'}"/>`).join('');
 // Clean reading band: texture remains at the perimeter, never behind labels.
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">${paths}<rect x="9" y="8" width="${width-18}" height="${height-16}" fill="${palette.canvas}"/></svg>`;
 const uri='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);cache.set(key,uri);return uri;
}
