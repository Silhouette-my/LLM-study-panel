# 开发与测试

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
npm ci
npm run build        # 构建固定查看器与 Node 工具
npm run demo         # 构建 + 全流程生成 build/model_atlas_demo.html
```

## 测试

```bash
pytest -q                       # Python：分析、校验、运行时（可选 PyTorch）
npm run typecheck               # TypeScript 类型检查
npm test                        # vitest：图投影、布局、对比、V2 场景
npm run test:e2e                # Playwright 浏览器回归（需 Chromium）
```

- 先 `npm run demo` 与 `pytest`，再跑 vitest / e2e：它们读取 `build/` 下生成的文件。
- 运行时测试需要 CPU PyTorch：`pip install torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu`；缺少时自动 skip。
- e2e 使用本机 Chromium：`MODEL_ATLAS_CHROMIUM=/path/to/chromium npm run test:e2e`；或 `npx playwright install chromium`。
- 环境禁止 `file://` 时：`MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e`，自动起本地 HTTP 服务（不是 file:// 验证）。

## Skill 打包

```bash
npm run pack-skill   # 得到 dist/model-atlas/ 与 dist/model-atlas-skill.zip
```

自包含包携带 SKILL.md、Python 工具、Schema、参考资料、教学输入和已编译资源，不含 node_modules / .venv / 密钥 / 权重。安装方式取决于宿主，详见 [GUIDE.md](GUIDE.md) 的 Skill 一节。
