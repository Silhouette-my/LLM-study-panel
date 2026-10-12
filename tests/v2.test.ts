import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import type {Architecture} from '../core/types';
import {project} from '../core/graph';
import {present} from '../core/presentation';
import {teachingGroups} from '../core/scene';
import {layoutGraph,routeViolations} from '../core/layout';
import {stableSeed,sketchNode,palette} from '../web/sketch';
import {compare} from '../core/compare';
const a=JSON.parse(readFileSync('build/laya-repository/decision.architecture.json','utf8')) as Architecture;
describe('V2 teaching scenes retain source truth',()=>{
 it('Reviewed groups are pinned, connected to every original node, and immutable',()=>{
  const before=JSON.stringify(a),g=present(a,project(a,'model',new Set()),false),groups=teachingGroups(a,g,'model');
  expect(groups.map(g=>g.label)).toEqual(['表征处理','评分路径','动作预测']);
  expect(groups.flatMap(g=>g.sourceNodeIds).sort()).toEqual(a.nodes.filter(n=>n.scope==='model').map(n=>n.id).sort());
  expect(new Set(groups.flatMap(g=>g.sourceNodeIds)).size).toBe(groups.flatMap(g=>g.sourceNodeIds).length);
  expect(groups.every(g=>g.kind==='teaching'&&g.snapshot===a.snapshot.id&&g.sourceRefs.length>0)).toBe(true);
  expect(g.edges.some(e=>e.source==='model/call:25'&&e.target==='model/call:27')).toBe(true); // score→softmax→act remains
  expect(g.edges.filter(e=>e.source==='model/input:input_ids').flatMap(e=>e.portPairs).some(([id])=>id.startsWith('model/input:marker_mask:'))).toBe(true);
  expect(g.edges.some(e=>e.conditions.length>0)).toBe(true);
  expect(JSON.stringify(a)).toBe(before);
 });
 it('Another source hash cannot inherit the reviewed task labels',()=>{
  const b=structuredClone(a);b.snapshot.sourceHash='different';
  const g=present(b,project(b,'model',new Set()),false),groups=teachingGroups(b,g,'model');
  expect(groups).toHaveLength(1);expect(groups[0].reviewer).toBe('structural view');
  expect(groups[0].label).not.toBe('评分路径');
 });
 it('Grouped routes attach to actual ports, avoid nodes, and are deterministic',async()=>{
  const g=present(a,project(a,'model',new Set()),false),groups=teachingGroups(a,g,'model');
  const one=await layoutGraph(g,groups),two=await layoutGraph(g,groups);
  expect(one).toEqual(two);expect(routeViolations(g,one)).toEqual([]);
 });
 it('Scene and layout do not change comparison results or parameter counts',async()=>{
  const b=structuredClone(a),before=compare(a,b),g=present(a,project(a,'model',new Set()),false);
  await layoutGraph(g,teachingGroups(a,g,'model'));
  expect(compare(a,b)).toEqual(before);expect(a.snapshot.parameterCount).toBeNull();expect(a.snapshot.executed).toBe(false);
 });
});
describe('Stable, offline sketch decoration',()=>{
 it('Uses valid fixed seeds and caches identical geometry independently of selection',()=>{
  const seed=stableSeed('model/scorer');expect(Number.isInteger(seed)).toBe(true);expect(seed).toBeGreaterThan(0);expect(seed).toBeLessThan(2147483647);
  const one=sketchNode('model/scorer',200,76,palette.module),two=sketchNode('model/scorer',200,76,palette.module);
  expect(one).toBe(two);expect(one).toMatch(/^data:image\/svg\+xml/);
  const svg=decodeURIComponent(one.split(',').slice(1).join(','));expect(svg).toContain('<path');expect(svg).not.toMatch(/<script|<image|onload|href=/);
  expect(sketchNode('different',200,76,palette.module)).not.toBe(one);
 });
});
