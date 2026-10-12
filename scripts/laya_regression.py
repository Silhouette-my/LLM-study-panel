"""Rebuild the supplied Laya snapshot and recovered excerpt; never run Laya."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/laya-diagnosis'
OUT.mkdir(parents=True, exist_ok=True)

def cli(*args):
    subprocess.run([sys.executable, '-m', 'model_atlas.cli', *map(str, args)], cwd=ROOT, check=True)

config = OUT / 'excerpt-config.json'
config.write_text('{}\n')
original = ROOT / 'tests/fixtures/laya_original.architecture.json'
recovered = ROOT / 'tests/fixtures/laya_decision_excerpt.py'
cli('validate', original)
cli('build', '--input', original, '--out', OUT / 'original-data.html')
result = OUT / 'reanalyzed.architecture.json'
cli('analyze', '--source', recovered, '--entry', 'DecisionModel', '--config', config, '--out', result)
doc = json.loads(result.read_text())
reason = '本次仅从用户 HTML 恢复 DecisionModel 嵌入片段，并保留原始行号。不是完整 common.py；原文件完整内容哈希无法复核，encoder 与辅助函数源码未提供。修复后仍是局部静态提取，没有运行 laya。'
doc['limitations'].append(dict(reason=reason, sourceRef=None, scope='model'))
result.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
with result.with_suffix('.report.md').open('a') as report:
    report.write('\n## 恢复片段的来源边界\n\n' + reason + '\n')
cli('validate', result)
cli('build', '--input', result, '--out', OUT / 'laya-reanalyzed.html')
print(OUT / 'laya-reanalyzed.html')
