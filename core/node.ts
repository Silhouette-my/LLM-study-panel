import {readFileSync} from 'node:fs';
import {compare} from './compare';
import {validate,validateBundle} from './validate';
import type {Architecture} from './types';
try{const payload=JSON.parse(readFileSync(0,'utf8'));const action=process.argv[2];let result:unknown;
 if(action==='compare'){const left=validate(payload.left),right=validate(payload.right);if(left.kind!=='architecture'||right.kind!=='architecture')throw Error('需要架构');result=compare(left as Architecture,right as Architecture);}
 else if(action==='validate'){validate(payload);result={valid:true};}
 else if(action==='bundle'){validateBundle(payload);result={valid:true};}
 else throw Error('未知操作');process.stdout.write(JSON.stringify(result));
}catch(e){process.stderr.write(String(e));process.exitCode=1;}
