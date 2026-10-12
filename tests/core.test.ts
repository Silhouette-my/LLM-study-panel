import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {project,teachingLayers,dependencies} from '../core/graph';
import {compare,correct} from '../core/compare';
import {parse,validate,validateComparison,associateNotes} from '../core/validate';
import type {Architecture,Session} from '../core/types';
const left=JSON.parse(readFileSync('build/mha.architecture.json','utf8')) as Architecture;
const right=JSON.parse(readFileSync('build/gqa.architecture.json','utf8')) as Architecture;
const copy=<T,>(x:T):T=>JSON.parse(JSON.stringify(x));
describe('不可变图投影',()=>{
 it('展开折叠保留残差与所有可见作用域边',()=>{
  const before=JSON.stringify(left),collapsed=project(left,'model',new Set());
  const expanded=project(left,'model',new Set(['model/blocks.0','blocks.0/attention','blocks.0/mlp']));
  const ids=expanded.edges.flatMap(e=>e.originalEdgeIds);
  const active=new Set(['model','blocks.0','blocks.0.attention','blocks.0.mlp']);
  expect(ids.sort()).toEqual(left.edges.filter(e=>active.has(e.scope)).map(e=>e.id).sort());
  const residual=expanded.edges.filter(e=>e.target==='blocks.0/residual1');expect(residual).toHaveLength(2);
  expect(project(left,'model',new Set())).toEqual(collapsed);expect(JSON.stringify(left)).toBe(before);
 });
 it('分支步进只是依赖层，保留多分支',()=>{
  const g=project(left,'blocks.0.mlp',new Set());const layers=teachingLayers(g);
  expect(layers.some(l=>l.includes('blocks.0.mlp/gate_proj')&&l.includes('blocks.0.mlp/up_proj'))).toBe(true);
  expect(dependencies(g,'blocks.0.mlp/down_proj','backward').has('blocks.0.mlp/x')).toBe(true);
 });
 it('汇总多边保存 originalEdgeIds/端口/张量数量及形状不一致',()=>{
  const d=copy(left);const e=d.edges.find(e=>e.scope==='blocks.0.mlp')!;
  d.edges.push({...e,id:'duplicate',tensor:'different'});d.tensors.push({...d.tensors.find(t=>t.id===e.tensor)!,id:'different',shape:[99]});
  const g=project(d,'blocks.0.mlp',new Set());const merged=g.edges.find(x=>x.originalEdgeIds.includes('duplicate'))!;
  expect(merged.count).toBe(2);expect(merged.tensorIds).toHaveLength(2);expect(merged.portPairs).toHaveLength(2);expect(merged.shape).toContain('多种形状');
 });
 it('多输出子作用域绑定完整并可往返',()=>{
  const d=copy(left),s=d.scopes.find(s=>s.id==='blocks.0')!,owner=d.nodes.find(n=>n.id===s.owner)!,out=d.nodes.find(n=>n.id==='blocks.0/output')!;
  const pp=d.ports.find(p=>p.id===owner.id+':out')!,cp=d.ports.find(p=>p.id===out.id+':in0')!;
  d.ports.push({...pp,id:owner.id+':out2',name:'extra'});d.ports.push({...cp,id:out.id+':in1',name:'extra'});
  s.bindings.push({parentPort:owner.id+':out2',childPort:out.id+':in1'});
  const e=d.edges.find(e=>e.source===owner.id+':out')!;d.edges.push({...e,id:'extra-edge',source:owner.id+':out2'});
  const before=JSON.stringify(d);const g=project(d,'model',new Set([owner.id]));expect(g.edges.flatMap(e=>e.originalEdgeIds)).toContain('extra-edge');expect(JSON.stringify(d)).toBe(before);
 });
});
describe('共享对比引擎',()=>{
 it('KV-only变化与配置/形状/参数/理论估算',()=>{const c=compare(left,right);expect(c.summary.parameterDelta).toBe(-12288);expect((c.summary.theoreticalCache as any).ratio).toBe(.25);expect(c.differences.some(d=>d.type==='shape'&&d.text.includes('k_proj'))).toBe(true);expect(c.differences.filter(d=>d.type==='configuration')).toHaveLength(1);expect(c.differences.some(d=>d.type==='topology')).toBe(false);});
 it('重命名提候选，报告实现变化而非无条件架构增删',()=>{const d=copy(left);d.nodes[0].label='renamed token input';const c=compare(left,d);expect(c.differences.some(d=>d.type==='implementation')).toBe(true);expect(c.differences.some(d=>d.type==='topology')).toBe(false);});
 it('连接改变与共享变化',()=>{const d=copy(left);d.parameters[0].shared=true;const e=d.edges[0];e.target=d.edges[1].target;const c=compare(left,d);expect(c.differences.some(d=>d.type==='sharing')).toBe(true);expect(c.differences.some(d=>d.type==='topology')).toBe(true);});
 it('拒绝/人工分组重算差异与未匹配，不只改高亮',()=>{const c=compare(left,right);const fixed=correct(left,right,c,{left:['blocks.0.attention/q_proj'],right:['blocks.0.attention/k_proj','blocks.0.attention/v_proj']});expect(fixed.matches.at(-1)?.origin).toBe('manual');expect(fixed.matches.filter(m=>m.status==='rejected').length).toBeGreaterThan(0);expect(fixed.differences.some(d=>d.type==='unknown'&&d.text.includes('多对多'))).toBe(true);expect(fixed.differences.some(d=>d.type==='shape'&&d.match===fixed.matches.at(-1)?.id)).toBe(true);});
 it('不同快照拒绝导入；未知保持建议',()=>{const c=compare(left,right);expect(()=>validateComparison({...c,leftSnapshot:'wrong'},left,right)).toThrow('快照');const d=copy(right);d.nodes[0].opaque=true;expect(compare(left,d).differences.some(d=>d.type==='unknown')).toBe(true);});
 it('CLI 生成与共享函数一致',()=>{const c=JSON.parse(readFileSync('build/mha_vs_gqa.comparison.json','utf8'));expect(c).toEqual(compare(left,right));});
});
describe('数据安全校验',()=>{
 it('Schema/语义/规模/JSON错误',()=>{expect(()=>parse('broken')).toThrow();const d=copy(left);d.edges[0].target='missing';expect(()=>validate(d)).toThrow();const huge=copy(left);huge.nodes=Array.from({length:3001},()=>huge.nodes[0]);expect(()=>validate(huge)).toThrow('3000');expect(()=>parse(' '.repeat(12_000_001))).toThrow('12 MB');expect(()=>parse('{"kind":"session","schemaVersion":"1.0","notes":[],"__proto__":{"polluted":true}}')).toThrow();expect(({} as any).polluted).toBeUndefined();});
 it('笔记旧快照保留待关联，原始文档不改',()=>{const s:Session={kind:'session',schemaVersion:'1.0',notes:[{snapshot:'old',anchor:'model/embedding',status:'review',text:'</script><script>BAD</script>',association:'exact'}]};expect(associateNotes(s,[left]).notes[0].association).toBe('pending');expect(s.notes[0].association).toBe('exact');});
});

import {coverage} from '../core/coverage';
describe('覆盖状态不能把未知边界伪装成完整模型',()=>{
 it('旧边界快照提示不足；支持教学数据不受影响',()=>{
  const d=copy(left);d.nodes=d.nodes.slice(0,2).map((n,i)=>({...n,role:i?'opaque':'input',opaque:true,childScope:null}));
  expect(coverage(d).status).toBe('boundary-only');
  expect(coverage(left).status).toBe('supported');
 });
 it('通用路径即使有明确 Sequential 子图，仍是局部提取',()=>{
  const d=copy(left);d.limitations.push({reason:'通用 AST 局部提取',scope:'model',sourceRef:null});
  expect(coverage(d).status).toBe('partial');expect(coverage(d).expandable).toBeGreaterThan(0);
 });
});
