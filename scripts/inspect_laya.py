"""Analyze a local Laya checkout as source data; do not import or run it."""
import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from model_atlas.analyzer import safe_path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', required=True)
parser.add_argument('--root', default='.', help='Allowed source/config read root')
parser.add_argument('--config', help='Actual analyze config; omission means unknown, not defaults')
parser.add_argument('--out', default='build/laya-repository')
args = parser.parse_args()
repo, out = Path(args.repo).resolve(), Path(args.out).resolve()
source = safe_path(repo / 'laya/common.py', args.root)
config = safe_path(args.config, args.root) if args.config else None
text = source.read_text(encoding='utf-8')
tree = ast.parse(text)
symbols = ['DecisionModel', '_DynamicMultiheadAttention', 'parallel_option_masks', 'build_model']
context = []
for name in symbols:
    node = next((n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name == name), None)
    if node is None:
        raise ValueError('Source symbol missing: ' + name)
    context.append(dict(symbol=name, path=str(source), start=node.lineno, end=node.end_lineno,
                        snippet='\n'.join(text.splitlines()[node.lineno - 1:node.end_lineno])))
out.mkdir(parents=True, exist_ok=True)
if config is None:
    config = out / 'unknown-config.json'
    config.write_text('{}\n')
    # CLI will apply the same explicit read root to this generated config.
    safe_path(config, args.root)
revision = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
dirty = bool(subprocess.run(['git', '-C', str(repo), 'status', '--porcelain'], capture_output=True, text=True, check=True).stdout.strip())
source_hash = hashlib.sha256(text.encode()).hexdigest()
metadata = dict(kind='repository-source-context', executed=False, revision=revision, workingTreeModified=dirty,
                sourceHash=source_hash, configProvided=args.config is not None,
                limitations=['配置未提供时所有维度保持未知，不套用 checkpoint 默认值。',
                             '函数片段是源码上下文，不代表已提取函数内部图。',
                             '不加载 checkpoint、不执行目标代码，不跟随 transformers 实现。'], symbols=context)
(out / 'source-context.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
for entry, filename in [('DecisionModel', 'decision'), ('_DynamicMultiheadAttention', 'attention')]:
    def cli(*arguments):
        subprocess.run([sys.executable, '-m', 'model_atlas.cli', *map(str, arguments)], check=True)
    result = out / (filename + '.architecture.json')
    cli('analyze', '--source', source, '--entry', entry, '--config', config, '--root', args.root, '--out', result)
    cli('validate', result)
    cli('build', '--input', result, '--out', out / (filename + '.html'))
print(json.dumps(dict(revision=revision, sourceHash=source_hash, output=str(out)), ensure_ascii=False))
