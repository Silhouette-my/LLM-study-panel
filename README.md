<div align="center">

# Model Atlas · 模型学习图谱

**读懂一个 PyTorch 模型，不该比跑它更难。**

把 PyTorch 单文件源码 + JSON 配置，变成一个**双击即开、完全离线**的交互式学习页面。

<a href="https://github.com/Silhouette-my/LLM-study-panel/blob/main/docs/media/model-atlas-promo.mp4"><img src="docs/media/model-atlas-promo-preview.webp" width="800" alt="Model Atlas 宣传片（点击观看 1080p 60fps 完整视频）"></a>

[▶ 完整交互宣传片](https://htmlpreview.github.io/?https://github.com/Silhouette-my/LLM-study-panel/blob/main/docs/promo/model-atlas-promo.html) · [快速开始](#快速开始) · [使用手册](docs/GUIDE.md) · [开发](docs/DEV.md)

</div>

## 特性

| | |
| --- | --- |
| 🔍 **逐级展开** | 整体 → Decoder Block → Attention / Gated MLP；单击旁侧看、双击进入、右键原地展开 |
| 🧮 **形状与源码联动** | 点任意边看张量形状、端口与条件；每个节点一键定位源码行 |
| ⚖️ **MHA / GQA 对比** | 双栏联动，建议对应关系可接受 / 拒绝 / 手工分组并重算差异，含理论 KV 缓存估算 |
| 📝 **学习笔记** | 独立导出 JSON，重新生成页面不丢笔记 |
| 🛡️ **诚实的静态分析** | 不执行你的代码、不下载权重、无需 GPU；未知结构明确标“未解析”，绝不凭空补全 |
| 📦 **单文件离线** | 无 CDN、无遥测、无网络请求，双击即开 |

## 快速开始

需要 Python ≥ 3.11 与 Node ≥ 22。

```bash
git clone https://github.com/Silhouette-my/LLM-study-panel.git
cd LLM-study-panel
python -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
npm ci
npm run demo
```

用浏览器打开 `build/model_atlas_demo.html`，即可看到 MHA / GQA 双模型对比演示。

## 分析你自己的模型

```bash
model-atlas analyze --source model.py --entry MyModel --config config.json --out build/my.architecture.json
model-atlas validate build/my.architecture.json
model-atlas build --input build/my.architecture.json --out build/my.html
```

先读生成的 `.report.md`，核对未解析项，再分享 HTML（页面包含源码快照，分享前请审查）。

| 命令 | 作用 |
| --- | --- |
| `analyze` | 静态解析源码 + 配置，输出架构 JSON 与覆盖报告 |
| `validate` | 校验 architecture / comparison / session 文档 |
| `compare` | 对比两个架构，生成差异与建议对应关系 |
| `build` | 生成单文件离线 HTML（单模型或双模型对比） |

## 能做什么、不能做什么

| ✅ 支持 | ❌ 不做 |
| --- | --- |
| 单文件 PyTorch 静态分析 | 执行用户源码、跨文件 import 追踪 |
| Linear / Embedding / LayerNorm / 激活、显式 `nn.Sequential`、残差、乘法、`torch.cat`、参数共享 | 展开 ModuleList、循环、动态分支（保留为 opaque 并继续提取后续语句） |
| 参数量与理论 KV 缓存估算 | 真实 cache、RoPE、激活 / 注意力数值、性能排名 |
| 教学 MiniDecoder 完整三级学习 | 官方 LLaMA 复现或权重兼容 |

详细边界见 [DESIGN.md](DESIGN.md) 与 [references/evidence.md](references/evidence.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [docs/GUIDE.md](docs/GUIDE.md) | 完整使用手册：离线操作、对比、笔记、MHA/GQA 证据口径 |
| [docs/DEV.md](docs/DEV.md) | 开发、测试、Skill 打包 |
| [DESIGN.md](DESIGN.md) · [SECURITY.md](SECURITY.md) | 实现取舍 · 安全边界 |
| [SKILL.md](SKILL.md) | Agent / Skill 工作流 |
| [references/](references) | 证据口径、视觉规范、V2 与 Laya 说明 |
| [CHANGELOG.md](CHANGELOG.md) · [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | 版本记录 · 第三方许可 |

## 项目结构

```
src/model_atlas/   Python CLI 与静态 AST 分析器
core/              TypeScript：图投影、布局、教学分组、对比引擎
web/               React + Cytoscape 查看器
schemas/           JSON Schema
examples/          教学 MiniDecoder 与 MHA/GQA 配置
scripts/  tests/   构建脚本 · 测试与固定 fixture
```
