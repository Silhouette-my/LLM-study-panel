# Changelog

## 0.1.1

- Canvas-first V2 学习界面：深紫黑画布、Rough.js 固定 seed 手绘纹理、带来源的教学分组（Laya 分组绑定已审查源码哈希）、检查器默认关闭、旁侧展开使用 UI-only 引用线。
- 通用 AST 分析器：Linear/Embedding/LayerNorm/激活、构造器 with、显式 Sequential、残差/乘法/`torch.cat`/多输出、别名共享；未知控制区域保留 opaque 边界并继续提取。
- “主流程 / 计算细节”可逆展示投影；未知形状显示“形状未确认”。
- MHA/GQA 双栏对比：建议接受/拒绝、一对多/多对一人工分组与差异重算、ComparisonDocument 导入导出。
- 笔记 SessionDocument 独立导入导出；schema 1.0 不变。
- 仓库整理：移除中间产物（`build/`、`dist/`、截图基线、诊断记录）、历史提示词与进度文档、一次性截图脚本；`build/` 与 `dist/` 加入 .gitignore；测试改用 `tests/fixtures/laya_decision.architecture.json`，不再依赖已删除的构建产物。
- 文档：重写 README，新增 CHANGELOG；Skill 打包改为携带 CHANGELOG.md。

## 0.1.0

- 初始版本：教学 MiniDecoder 三级学习闭环、MHA/GQA 静态对比、离线单文件 HTML、Skill 打包。
