import {build} from 'esbuild';
import './notices.mjs';
import Ajv from 'ajv';
import standaloneCode from 'ajv/dist/standalone/index.js';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
const dir='src/model_atlas/resources';mkdirSync(dir,{recursive:true});
const ajv=new Ajv({code:{source:true},strict:false,allErrors:false});
const refs={};for(const k of ['architecture','comparison','session']){const schema=JSON.parse(readFileSync(`schemas/${k}.schema.json`,'utf8'));schema.$id=k;ajv.addSchema(schema,k);refs[k]=k;}
writeFileSync('assets/validators.cjs',standaloneCode(ajv,refs));
await build({entryPoints:['core/node.ts'],bundle:true,platform:'node',format:'cjs',target:'node22',outfile:`${dir}/core.cjs`,legalComments:'eof'});
await build({entryPoints:['web/app.tsx'],bundle:true,platform:'browser',format:'iife',target:'es2022',outfile:`${dir}/viewer.js`,minify:true,legalComments:'eof'});
writeFileSync(`${dir}/viewer.css`,readFileSync('web/style.css'));
console.log('固定查看器和共享 Node 工具已构建');
