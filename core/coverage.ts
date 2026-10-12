import type {Architecture} from './types';
// Counts describe extraction coverage, not accuracy percentages or runtime proof.
export function coverage(a:Architecture){
 const operations=a.nodes.filter(n=>!['input','output','constant'].includes(n.role));
 const opaque=operations.filter(n=>n.opaque);
 const expandable=a.nodes.filter(n=>n.childScope);
 const boundaryOnly=operations.length===0||operations.every(n=>n.opaque);
 const generic=a.limitations.some(l=>l.reason.includes('通用 AST'));
 const partial=generic||opaque.length>0;
 return {status:boundaryOnly?'boundary-only':partial?'partial':'supported',operations:operations.length,opaque:opaque.length,expandable:expandable.length,unknownShapes:a.tensors.filter(t=>t.shape.includes(null)).length,parameterCount:a.snapshot.parameterCount};
}
