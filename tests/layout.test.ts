import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {layoutGraph,segmentStyle,routeViolations} from '../core/layout';
import {project} from '../core/graph';
import {overview} from '../core/presentation';
import type {Architecture} from '../core/types';
const laya=JSON.parse(readFileSync('tests/fixtures/laya_partial.architecture.json','utf8')) as Architecture;
const teaching=JSON.parse(readFileSync('build/mha.architecture.json','utf8')) as Architecture;
describe('Orthogonal routes follow the actual graph',()=>{
 for(const [name,doc,scope,summary] of [['Laya overview',laya,'model',true],['Laya detail',laya,'model',false],['Attention residuals',teaching,'blocks.0.attention',false]] as const){
  it(name,async()=>{
   const before=JSON.stringify(doc),raw=project(doc,scope,new Set()),g=summary?overview(raw):raw,layout=await layoutGraph(g);
   expect(Object.keys(layout.routes).sort()).toEqual(g.edges.map(e=>e.id).sort());
   expect(routeViolations(g,layout)).toEqual([]);
   for(const edge of g.edges){
    const source=layout.positions[edge.source],target=layout.positions[edge.target],points=layout.routes[edge.id],style=segmentStyle(points,source,target);
    const dx=target.x-source.x,dy=target.y-source.y,length=Math.hypot(dx,dy);
    style.weights.forEach((w,i)=>{
     expect(source.x+dx*w-dy/length*style.distances[i]).toBeCloseTo(points[i+1].x,6);
     expect(source.y+dy*w+dx/length*style.distances[i]).toBeCloseTo(points[i+1].y,6);
    });
   }
   expect(JSON.stringify(doc)).toBe(before);
  });
 }
});
