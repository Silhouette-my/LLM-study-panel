"""Allowlist packaging: no environment, credentials, weights, or unrelated files."""
import shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'dist/model-atlas'
if out.exists(): shutil.rmtree(out) # only this script's generated package directory
out.mkdir(parents=True)
for name in ['SKILL.md','README.md','DESIGN.md','SECURITY.md','PROGRESS.md','pyproject.toml','requirements.lock','THIRD_PARTY_NOTICES.md']:
 shutil.copy2(root/name,out/name)
for directory in ['schemas','references','examples']:
 shutil.copytree(root/directory,out/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copytree(root/'src/model_atlas',out/'src/model_atlas',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(out/'scripts').mkdir()
for script in ['demo.py', 'inspect_laya.py']:
 shutil.copy2(root/'scripts'/script,out/'scripts'/script)
# Bundled resources and standalone CLI are enough; no npm or source repo required.
shutil.make_archive(str(root/'dist/model-atlas-skill'),'zip',out.parent,out.name)
print(out)
