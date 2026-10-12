# Laya 本地效果诊断

用户上传 HTML 的结构化数据通过 Python 与 TypeScript 校验，内嵌查看器与本次修改前的构建产物一致。主要问题在生成数据的通用 AST 分析器，而非 HTML 文件损坏。

后续核对：用户提供完整 GitHub 仓库后，commit c4a805b5160621bbfc53417126990a67d3163bc5 的 common.py 哈希与上传记录完全一致。下文“完整哈希无法复核”描述的是当时仅恢复片段的阶段；现在已核对完整文件。新的完整文件产物在 build/laya-repository，进一步结论见 references/laya.md。

## 原始快照的实际覆盖

- 入口 DecisionModel，原源码定位 work/laya/laya/common.py:574–658；forward:609–658。
- 配置为空，静态 executed=false；10 节点、9 边、1 scope、0 注册实例、0 参数实体。
- 8 个 forward 参数输入、1 个首个 if 的未知边界、1 个未知输出；无可进入模块。
- 旧算法遇到 forward 第一个 if 就结束提取，遗漏 type_emb、head 控制区、gather、scorer、act_head 和真实两个返回值。
- 旧注册提取器只读取构造器顶层赋值，遗漏 with 内的 head/type_emb/scorer/act_head。外部传入 encoder 也未列出声明。
- 页面没有醒目说明覆盖不足，且把所有模型都标成“教学 Decoder，无 RoPE / KV cache”，对本例有误导。

## 0.1.1 修复与重建

未知控制区保持 opaque，并保留后续需要的命名结果边界，然后继续提取后续语句；不选择具体分支或假造循环次数。构造器 with/if 内声明保留上下文条件，外部 encoder 只列出声明。显式 Sequential 可按声明顺序进入；链式 scorer(m).squeeze().float() 保留接收者依赖。页面显示覆盖与未知统计，模块声明和静态调用分别查看。

使用 HTML 内嵌 DecisionModel 片段恢复，保留原行号。重建有 67 节点、77 边、3 scopes、12 注册实例，两个输出 logits/act_logits，可进入 scorer/act_head；不以数量等同于完整或正确执行路径。参数总数 null。

新源码哈希针对恢复片段，不能与原完整 common.py 哈希等同。原快照未修改：original-data.html 只用新版查看器包裹旧数据；laya-reanalyzed.html 才使用修复后的局部数据。

## 验证与剩余限制

Python 20 测试通过；TS 14 测试通过；typecheck、build 通过；本地 HTTP 转发浏览器 6 测试通过（包含两个 Laya 回归），Laya 页面 pageerror=0、除主文档外网络请求=0。没有运行 Laya、加载权重或测量其 shape。file:// 受宿主管理策略阻止，未将 HTTP 测试标为 file:// 通过。

仍缺少完整源码、实际 encoder 模型与配置、辅助函数和动态 Attention 实现，无法展示它们的内部结构或完整参数/形状。双向 encoder 加 decision head 的本例不能套入教学 decoder 的三级适配器。要继续支持真实内部浏览，需基于完整源码增加并验证相应适配器，而不是靠展开按钮补结构。

## 恢复命令

```
cd /workspace/LLM-study-panel
npm run build
.venv/bin/python scripts/laya_regression.py
.venv/bin/pytest -q --junitxml=build/laya-diagnosis/pytest-results.xml
npm test
.venv/bin/python scripts/demo.py
MODEL_ATLAS_CHROMIUM=/usr/bin/chromium MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e
npm run pack-skill
```

测试用原架构与恢复片段见 tests/fixtures/laya_*；来源声明在 laya_excerpt_provenance.json。用户本地完整模型应使用原始源码与实际 config 重新 analyze，而非拿恢复片段当完整源码。
