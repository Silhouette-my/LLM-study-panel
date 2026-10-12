import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def cli(*args): subprocess.run([sys.executable,'-m','model_atlas.cli',*args],cwd=root,check=True)
for name in ['mha','gqa']:
 cli('analyze','--source','examples/mini_decoder.py','--entry','MiniDecoder','--config',f'examples/configs/{name}.json','--out',f'build/{name}.architecture.json')
 cli('validate',f'build/{name}.architecture.json')
cli('compare','--left','build/mha.architecture.json','--right','build/gqa.architecture.json','--out','build/mha_vs_gqa.comparison.json')
cli('validate','build/mha_vs_gqa.comparison.json')
cli('build','--input','build/mha.architecture.json','--out','build/mha.html')
cli('build','--input','build/mha.architecture.json','--input','build/gqa.architecture.json','--comparison','build/mha_vs_gqa.comparison.json','--out','build/model_atlas_demo.html')
print('离线演示：'+str(root/'build/model_atlas_demo.html'))
