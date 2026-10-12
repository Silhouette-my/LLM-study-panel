import argparse
import json
import subprocess
import sys
from pathlib import Path
from importlib.resources import files
from .analyzer import analyze
from .validate import load, validate


def write(path, value):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def node_tool(action, payload):
    tool=files('model_atlas').joinpath('resources/core.cjs')
    if not tool.is_file(): raise ValueError('缺少构建资源；先执行 npm run build')
    try:
        result=subprocess.run(['node',str(tool),action],input=json.dumps(payload),text=True,capture_output=True,timeout=30)
    except FileNotFoundError as exc: raise ValueError('compare/build 需要 Node >=22') from exc
    if result.returncode: raise ValueError(result.stderr.strip())
    return json.loads(result.stdout)


def main():
    parser=argparse.ArgumentParser(prog='model-atlas')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('analyze')
    for arg in ['source','entry','config','out']: p.add_argument('--'+arg,required=True)
    p.add_argument('--root',default='.',help='允许读取根目录，含符号链接解析；默认当前目录')
    p=sub.add_parser('validate'); p.add_argument('input')
    p=sub.add_parser('compare')
    for arg in ['left','right','out']: p.add_argument('--'+arg,required=True)
    p=sub.add_parser('build'); p.add_argument('--input',action='append',required=True); p.add_argument('--comparison'); p.add_argument('--out',required=True)
    args=parser.parse_args()
    try:
        if args.command=='analyze':
            doc=analyze(args.source,args.entry,args.config,args.root); write(args.out,doc)
            operations=[n for n in doc['nodes'] if n['role'] not in ('input','output','constant')]
            expandable=sum(bool(n['childScope']) for n in doc['nodes'])
            opaque=sum(n['opaque'] for n in operations)
            partial=any('通用 AST' in l['reason'] for l in doc['limitations']) or opaque>0
            coverage=f'覆盖：{"局部静态提取（非完整架构）" if partial else "受支持教学适配器"}；可进入模块 {expandable}；未解析计算/结果边界 {opaque}。\n'
            report=f"# {args.entry} 分析报告\n\n快照：{doc['snapshot']['id']}\n模式：静态 AST；未执行目标源码；无运行验证。\n节点：{len(doc['nodes'])}；独立参数实体：{len(doc['parameters'])}；参数数：{doc['snapshot']['parameterCount']}。\n证据："+json.dumps({k:sum(e['kind']==k for e in doc['evidence']) for k in ['source','config','static','unknown','runtime']},ensure_ascii=False)+"\n\n覆盖与未知：\n"+'\n'.join('- '+x['reason'] for x in doc['limitations'])+'\n'
            report=report.replace('模式：静态 AST；未执行目标源码；无运行验证。\n','模式：静态 AST；未执行目标源码；无运行验证。\n'+coverage)
            write(str(Path(args.out).with_suffix('.report.md')),report)
            if partial:
                print('Model Atlas 提示：局部静态提取，不能当成完整架构；请核对分析报告中的未知项。',file=sys.stderr)
        elif args.command=='validate':
            doc=validate(load(args.input)); node_tool('validate',doc); print('有效文档：'+doc['kind'])
        elif args.command=='compare':
            left,right=validate(load(args.left)),validate(load(args.right))
            result=node_tool('compare',dict(left=left,right=right)); validate(result); write(args.out,result)
        else:
            docs=[validate(load(x)) for x in args.input]
            if not 1<=len(docs)<=2 or any(x['kind']!='architecture' for x in docs): raise ValueError('build 需要 1–2 份架构文档')
            comp=validate(load(args.comparison)) if args.comparison else None
            payload=dict(architectures=docs,comparison=comp)
            node_tool('bundle',payload)
            js=files('model_atlas').joinpath('resources/viewer.js').read_text()
            css=files('model_atlas').joinpath('resources/viewer.css').read_text()
            data=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
            # Viewer is trusted build output; source/data never inserted into executable script.
            html='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data: blob:; connect-src \'none\'; worker-src \'none\'"><title>Model Atlas</title><style>'+css+'</style></head><body><div id="root"></div><script id="atlas-data" type="application/json">'+data+'</script><script>'+js.replace('</script','<\\/script')+'</script></body></html>'
            write(args.out,html)
        return 0
    except (ValueError,OSError,SyntaxError,KeyError,StopIteration,subprocess.TimeoutExpired) as exc:
        print('Model Atlas 错误：'+str(exc),file=sys.stderr); return 1

if __name__=='__main__': sys.exit(main())
