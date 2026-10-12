import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {project,teachingLayers} from '../core/graph';
import {overview,present,shapeLabel,edgeLabel} from '../core/presentation';
import type {Architecture} from '../core/types';
const laya=JSON.parse(readFileSync('tests/fixtures/laya_partial.architecture.json','utf8')) as Architecture;
describe('Readable display projections preserve their evidence',()=>{
 it('Contracts helpers without losing edges or changing the source architecture',()=>{
  const before=JSON.stringify(laya),raw=project(laya,'model',new Set()),g=overview(raw);
  expect(g.nodes.length).toBeLessThan(raw.nodes.length/2);
  expect([...g.edges.flatMap(e=>e.originalEdgeIds),...g.internalEdgeIds].sort()).toEqual(raw.edges.flatMap(e=>e.originalEdgeIds).sort());
  expect(Object.values(g.members).flat().sort()).toEqual(raw.nodes.map(n=>n.id).sort());
  expect(teachingLayers(g).flat().length).toBe(g.nodes.length);
  expect(g.nodes.filter(n=>n.role==='output').map(n=>n.label)).toEqual(['输出 logits','输出 act_logits']);
  expect(g.nodes.filter(n=>n.childScope).map(n=>n.label)).toEqual(['self.scorer','self.act_head']);
  expect(JSON.stringify(laya)).toBe(before);
 });
 it('Full calculation view restores every original node and edge',()=>{
  const raw=project(laya,'model',new Set());
  expect(present(laya,raw,true).nodes).toEqual(raw.nodes);
  expect(present(laya,raw,true).edges).toEqual(raw.edges);
 });
 it('Unknown shapes remain unknown without repeated null labels',()=>{
  expect(shapeLabel([null])).toBe('形状未确定');expect(shapeLabel(['B',null,64])).toBe('[B, ?, 64]');
  expect(edgeLabel('[null]')).toBe('');expect(edgeLabel('["B",null,64]')).toBe('');
  expect(edgeLabel('["B","T",64]')).toBe('[B, T, 64]');
 });
});
