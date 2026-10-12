# Model Atlas 实际进度

2026-10-11：仓库仅有 README；检查 /AGENTS.md、/workspace/AGENTS.md 及仓库，未发现 AGENTS.md。完整读取用户附件，保存需求副本。
环境：Python 3.12.14、Node 24.19.0、npm 11.9.0；最初未安装 torch/pytest，已有 jsonschema。
完成：项目骨架、真实 CPU 教学模型及 MHA/GQA 配置。
进行中：静态分析器、数据契约。模型分析不执行输入源码。
恢复：cd /workspace/LLM-study-panel；查看本文件，继续运行 README 命令。
尚未运行测试，不宣称通过。

## 首轮实际命令与结果

- `npm install` / `pip install -e '.[test]'`：默认 sandbox 无网络失败。启用允许网络后 pip 成功；npm 默认缓存不可写，改 `--cache /tmp/model-atlas-npm`。
- 初次 @types/cytoscape=3.31.9 不存在；`npm view @types/cytoscape version` 核实为 3.31.0。修正后 npm 安装成功，记录 package-lock。
- `.venv/bin/pip install torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu`：成功，CPU 2.9.0+cpu，不下载权重/CUDA。
- `.venv/bin/pytest -q --junitxml=build/pytest-results.xml`：10 passed；包括独立 CPU 教学运行。
- `npm test`：12 passed；图投影、残差/分支/多输出/汇总边、对比/人工重算、Schema/安全导入。
- `npm run typecheck` 首次一处 Cytoscape callback 返回类型错误，修复后通过。
- `PATH="$PWD/.venv/bin:$PATH" npm run demo`：成功，生成两份 architecture、comparison、报告、单/双 HTML。
- `npx playwright install chromium`：域名策略 403 拒绝下载。没有修改网络策略或改用下载绕行。
- 找到系统 `/usr/bin/chromium` 154.0.8037.57。默认 sandbox launch 在 setsockopt 被拒；允许网络上下文后可启动。
- `MODEL_ATLAS_CHROMIUM=/usr/bin/chromium npm run test:e2e`：3 failed，全部在 file:// 导航时 ERR_BLOCKED_BY_ADMINISTRATOR。已读取管理策略确认 URLBlocklist=* 且未允许 file://；未修改策略。原失败记录 build/playwright-file-results.json。
- 后续 HTTP fallback 使用完全相同 HTML，仅用于交互与安全验证，不视为 file:// 验收通过。该模式 `MODEL_ATLAS_E2E_HTTP=1`，结果单独保存。

当前限制：file:// 浏览器验收因宿主管理策略未完成；其余测试、打包与恢复说明继续完善。

## 最终验证与交付（2026-10-11，中国标准时间）

实现：Python 静态 analyze/validate/build、共享 TS compare 与修正、版本化 Schema/语义校验、固定 React/Cytoscape/ELK 查看器、真实教学 MHA/GQA、两个 HTML 闭环、来源/形状/解释/笔记、架构/Session/Comparison 导入导出、自包含 Skill。

最终实际命令：

- `npm run typecheck`：通过，无类型错误。
- `PATH="$PWD/.venv/bin:$PATH" npm run demo`：通过；两份架构 JSON + 报告、对比 JSON、单/双模型 HTML。81 静态节点/模型；source 81、config 8、static 102、runtime 0。
- `.venv/bin/pytest -q --junitxml=build/pytest-results.xml`：**13 passed，0 skipped**。新增未知注册/部分权重共享的 null 统计与无关源码排除检查。默认 analyze 不执行源码的副作用测试通过。
- `npm test`：**12 passed**。共享 CLI/浏览器比较函数结果一致，人工修正重算、分支/多输出/残差/原始边映射/往返、导入校验。
- `MODEL_ATLAS_CHROMIUM=/usr/bin/chromium MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e`（需宿主允许 socket）：**4 passed**，使用本地 127.0.0.1:8765 转发。1366×768、1920×1080；三级进入、原地展开折叠、面包屑、搜索、实际图边点击、依赖高亮、选择不重排、返回恢复相机/选择、源码、教学步进、双栏联动、人工修正/接受拒绝与重算、笔记下载恢复、恶意/超限导入与初始 script 逃逸验证。控制台错误 0，除启动 HTML 主文档外 HTTP(S) 请求 0。build/playwright-http-results.json，辅助截图 build/offline-{1366,1920}.png（命名沿用，实际使用 HTTP 转发）。
- 本地转发按用户后续指示执行；没有把该模式标记为 file:// 验证。**file:// 直接打开仍未完成运行验收**，宿主 URL 管理策略阻止导航，历史失败记录 build/playwright-file-results.json。单文件资源内联和 CSP 已通过本地转发实际运行。正常允许 file:// 的桌面浏览器可以自行执行原测试命令。
- CPU 教学运行：torch 2.9.0+cpu、seed=2026、float32、eval、tokens=[2,4]。MHA/GQA logits 都 [2,4,128]；Q=[2,4,64]；K/V=[2,4,64]/[2,4,16]；复制前 K/V=[2,8,4,8]/[2,2,4,8]，复制后均 [2,8,4,8]；每层 KV 参数差 6144，总差 12288。完整模型参数 98624/86336，与静态统计一致。独立报告 build/runtime_observations.json；静态 architecture.executed=false，不混入 runtime 证据。
- 理论缓存未测量：未复制 KV 存储、B=2、T_cache=4、float32、layers=2 时 8192/2048 bytes，比例 1/4。模型没有实际缓存或速度测量。
- `npm run pack-skill`：生成 dist/model-atlas 与 dist/model-atlas-skill.zip。白名单打包，包含必要构建资源、Schema、Skill、说明、许可证；无 node_modules/.venv/密钥/权重。
- 在 `/tmp/model-atlas-isolated/final-skill` 独立复制最终包；新虚拟环境 `/tmp/model-atlas-isolated/venv` pip 安装非 editable 包，模块路径位于该 venv/site-packages。`env -u PYTHONPATH .../python scripts/demo.py` 完整通过；再 analyze/validate 通用 BranchShared 通过。原仓库 npm/Python 源目录不是运行依赖。
- 许可证：npm 已安装包核对并保留 THIRD_PARTY_NOTICES.md 与包资源副本；未引用可选外部 ml-architecture-diagram-skill 代码。
- 尝试 Codex open_in_codex 展示浏览器，宿主返回 No handler registered，未声称已打开。演示本地服务实际启动于 127.0.0.1:8787（exec session 1459）；最终查看器仍为独立单文件。

### 保留边界 / 未实现

通用分析仅单文件受限 AST；动态条件、循环、未知自定义运算/复杂共享保留 opaque/未知参数统计；拼接/输入完整 shape 未确认。教学适配器任意 AST 结构变化整体降级。重复层异构场景未猜测模板。跨模型家族对应、运行采样 trace、真实执行回放、RoPE、KV cache、注意力数值、性能测量未实现。自动/人工对应均非数学等价证明。旧快照笔记保留待关联，未做不可靠的自动迁移。Skill 未修改全局宿主设置，未验证桌面插件实际激活。

### 恢复与重新验证

```
cd /workspace/LLM-study-panel
source .venv/bin/activate
npm run demo
pytest -q --junitxml=build/pytest-results.xml
npm run typecheck
npm test
MODEL_ATLAS_CHROMIUM=/usr/bin/chromium MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e
npm run pack-skill
```

若宿主允许 file://，移除 MODEL_ATLAS_E2E_HTTP 重跑浏览器测试。若需要本地预览：`python -m http.server 8787 --bind 127.0.0.1 --directory build`，浏览器访问 http://127.0.0.1:8787/model_atlas_demo.html。修改教学源码前先导出个人 SessionDocument；重新分析后导入笔记，失配锚点留 pending。

## Laya 上传快照诊断与修复（2026-10-12，中国标准时间；UTC 10-11）

读取用户上传 laya-model-atlas.html 作为数据，不执行内嵌模型源码。HTMLParser 提取 atlas-data，Python/TS validate 均通过；上传 viewer 与修改前受信构建字节一致。原 DecisionModel 图只有 8 输入 + 第一个 if opaque + 未知输出；构造器 with 内模块丢失，forward 在首个 if 停止。配置为空，encoder 外部注入；不能推断 backbone/Attention/参数或 shape。

简短实施计划：修复通用控制区后的继续提取、with 内注册与显式 Sequential；补覆盖提示和注册声明查看；用真实上传片段回归、重建并交付。已完成。

0.1.1：独立 generic.py，未知控制区域和条件结果保留源码边界，后续语句继续；潜在提前返回附条件；构造器上下文/条件声明及外部 callable 声明保留；显式 Sequential 子层绑定和接收者链式依赖；不猜测未知输入 rank/dtype。页面声明树独立于调用图，新增醒目覆盖提示，去除通用模型的错误教学 decoder 标记。CLI 报告同样说明局部覆盖。更新 README/DESIGN/SKILL/证据说明。

实际命令与结果：

- `.venv/bin/pytest -q --junitxml=build/laya-diagnosis/pytest-results.xml`：20 passed（7 新回归，含源文件副作用不执行、条件覆盖/循环/提前返回、Sequential 参数与真实 Laya 片段）。
- `npm run typecheck`、`npm run build`：通过。
- `.venv/bin/python scripts/demo.py`：教学两个闭环构建通过。
- `model-atlas analyze/validate/build` 恢复片段：通过；67 节点/77 边/3 scopes/12 注册实例，0 已确认参数实体，参数总数 null。两个实际输出和 scorer/act_head 子作用域保留。增加来源边界 limitation；未运行 Laya。
- `.venv/bin/python scripts/laya_regression.py`：可复现构建原数据+新版查看器、修复后片段+新版查看器；测试 fixtures 保留来源声明。
- `npm test`：14 passed（含覆盖不足与通用范围分类）。
- `MODEL_ATLAS_CHROMIUM=/usr/bin/chromium MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e`（允许本地 socket）：6 passed，新增两项 Laya 页面回归；既有学习/对比/安全导入测试也通过。Laya pageerror=0，非主文档 HTTP 请求=0。HTTP 转发验证，不声称 file:// 通过。

交付位置：build/laya-diagnosis/DIAGNOSIS.md、reanalyzed.architecture.json/.report.md、laya-reanalyzed.html、reanalyzed-preview.png；更新 dist/model-atlas-skill.zip。源码只来自上传 HTML 的 DecisionModel 片段，保留原行号，不是完整 common.py，其完整哈希无法复核。encoder、自定义 Attention、辅助函数、动态 head 仍未展开，Laya 运行形状/参数未验证。

恢复：按本次 DIAGNOSIS.md 命令重建；进一步展开 Laya 需要用户提供实际 analyze 命令、完整源码和 encoder/config 信息，已有异步问题待回复。未提交或推送 GitHub。

最终补充：修正通用张量面板的固定“最后一维由配置推导”文字，改为证据确认/null 未知。重建后单独重跑 Laya 浏览器回归 2 passed（6.1 秒），报告 build/laya-diagnosis/playwright-laya-results.json；此后默认 playwright-http-results.json 记录的是这两项，完整 6 项通过见上述实际命令输出。重新 pytest 20 passed。`pip wheel --no-deps --no-build-isolation dist/model-atlas` 构建 0.1.1 wheel 成功，在原独立 /tmp/model-atlas-isolated/venv 用非 editable wheel 升级成功；该 venv 对真实 Laya 片段 analyze/build 成功，未执行 Laya。最终重新 pack-skill，工具包含最新 PROGRESS 和查看器。

## 用户提供完整 Laya 仓库后的核对（2026-10-12，中国标准时间）

使用 cloud-environment:cloud-environment-runtime 技能读取网络说明和环境状态，GitHub 在已实施允许策略中；未修改策略或读取凭证。实际 `git clone --depth 1 https://github.com/NandhaKishorM/laya.git /workspace/laya-source` 成功，commit c4a805b5160621bbfc53417126990a67d3163bc5。读取该 checkout 的 AGENTS.md；仅作为分析输入，不修改上游，不宣称上游 CI 通过。

common.py SHA256 f8e4c7408fb72e4088f4ac6db3c6764b387a955aea978e8360e0c189615a9505，与上传 HTML 的完整文件哈希一致。由此确认首个 if 和 with 注册遗漏来自分析器，而非本地版本差异。build_model 根据 checkpoint encoder/config 构造 AutoModel；n_act 是 len(act_costs)+1，head_layers 来自 cfg。读取 agent.py 和 verify/checkpoints.json，确认英文/typed-decisions 使用 ModernBERT-large、多语言 mmBERT-base 的仓库声明；不据此认定用户本地模型。仓库没有真实 rl_agent_config.json/encoder/config.json；已异步询问用户 checkpoint 与实际配置。

新增可复用 scripts/inspect_laya.py：读取允许根内实际 common.py，构建两个独立分析/HTML，保存四个相关源码符号上下文和 Git/哈希来源；省略配置明确为空，不导入/执行 Laya，不选择 checkpoint。打包包含该脚本和 references/laya.md。未新增或冒称 head/encoder 三级适配器。

实际验证命令：

- `.venv/bin/model-atlas analyze --source /workspace/laya-source/laya/common.py --entry DecisionModel / _DynamicMultiheadAttention --config ... --root /workspace --out ...`，两入口均成功；validate/build 成功。
- `.venv/bin/python scripts/inspect_laya.py --repo /workspace/laya-source --root /workspace --out build/laya-repository`：成功，可复现完整文件构建；Decision 67 节点/77 边/3 scopes/12 声明；Attention 34 节点/47 边/1 scope/0 已确认声明，参数总数均 null、executed=false。
- `node build/laya-repository/check.mjs`（允许本地 socket）：本地 HTTP 转发两页面 passed；Decision 两输出可见，Attention 的 scaled_dot_product_attention 源码定位通过；pageerror/consoleerror=0，非主文档网络请求=0。build/laya-repository/browser-results.json 与两个 preview.png。未重跑不受影响的既有测试；上轮 20 Python/14 TS/6 浏览器结果仍记录于上文，不宣称本轮重跑。
- `npm run pack-skill`：更新包；`git diff --check` 无错误。

交付：build/laya-repository/decision.html、attention.html、各 architecture/report、source-context.json；核对说明 references/laya.md。Attention 是独立部分分析，未接为 DecisionModel.head 内的可进入 scope；动态投影分支、继承参数、外部 transformers encoder 仍未展开。补充形状与参数公式仅在文档中按明确假设解释，不写入运行证据。未加载权重或运行 Laya；未提交/推送 GitHub。

恢复：执行上述 inspect_laya 命令；源码 checkout 本次仅用于只读分析，不打包第三方完整仓库。若用户提供 checkpoint/config，再选择该真实实现做适配及验证，不能把仓库列表/构造器默认值当成用户本地配置。

## null 与页面杂乱的改进（2026-10-12，中国标准时间）

用户反馈实际截图：逐表达式图、长标签和重复 [null] 导致阅读困难。说明 null 是形状推导未知，不是模型返回空值；当前没有 encoder/input contract，通用分析器也未支持此类动态分支完整 shape 传播。没有为消除 null 猜测维度。

实施：新增 core/presentation.ts 的主流程展示投影，辅助节点只向唯一后继收缩、同 scope 无入边输入合并；原始组成节点及内部/外部 originalEdgeIds/portPairs/tensorIds 完整保留。原架构不修改；两输出和真实模块进入保持。Laya 顶层 56 原节点默认汇总为 12 个展示节点，可切计算细节完整恢复。汇总仅是视图，不创建模块或运行步骤。缩短画布/侧栏标签，未知形状连线不重复显示 null，张量面板显示“形状未确认”或 ?；收起覆盖明细与分析限制，移除大型多行节点 chip 区，改窄列表；主流程自动适配全部图并提高缩放后字体可读性。更新 README/DESIGN/SKILL，刷新所有教学与 Laya HTML。

实际命令与结果：

- `npm run typecheck`：通过。
- `npm test`：最终 17 passed，新增 3 项投影保真/不变性、完整视图恢复、未知维度表示。首次新增测试未被旧 Vitest 单文件 include 收集，已改为 tests/*.test.ts 后实际运行通过，不把初次 14 项当作新测试通过。
- `npm run build`、`.venv/bin/python scripts/demo.py`、`scripts/laya_regression.py`、`scripts/inspect_laya.py --repo /workspace/laya-source --root /workspace --out build/laya-repository`：全部成功。
- 浏览器首轮 4 passed/2 failed：旧断言仍期待 JSON 带引号的 ["B","T",64]，新版展示为 [B, T, 64]；按真实显示格式更新断言后重跑完整套件。`MODEL_ATLAS_CHROMIUM=/usr/bin/chromium MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e`：7 passed（19.4 秒）。新增主流程节点减少、未知边标签不出现 null、组成细节可恢复、默认明细折叠、模块进入/源码/未知提示的 Laya 回归。完整报告 build/laya-diagnosis/playwright-ui-full-results.json。
- 最后缩短标签/调整字体后，单独 Laya 回归 3 passed（5.9 秒）；默认 playwright-http-results.json 是这三项的最新报告。`node build/laya-repository/check.mjs`：实际完整文件 Decision/Attention 两页面 passed，0 页面/控制台错误、0 非主文档网络请求。Decision 主流程截图已人工查看：全部输出可见，未反复标注 null。HTTP 转发，不声称 file:// 测试通过。
- `npm run pack-skill`、`git diff --check`：成功。分析代码本轮未改，不重跑 Python/真实模型运行测试；历史 20 项 Python 通过不宣称本轮重跑。

交付：build/laya-repository/decision.html 和 attention.html（完整文件）、build/laya-diagnosis/laya-reanalyzed.html（恢复片段），新版预览 build/laya-repository/decision-preview.png；工具 dist/model-atlas-skill.zip。旧 HTML 内嵌旧查看器，安装新工具不会自动改变旧文件，需要重新 build 或打开新版 HTML。源码与形状数据仍为原静态未知结果，encoder/head 三级适配尚未实现。

恢复：npm run build；先 scripts/demo.py 和 scripts/laya_regression.py，再 npm test/typecheck/浏览器回归；完整文件页面运行 inspect_laya.py。未来 shape 支持需真实输入/config 与适配验证，不仅调整 UI。没有提交或推送 GitHub。

## 参考原绘图仓库的美术与正交布局（2026-10-12，中国标准时间）

用户要求节点/连线尽量横平竖直，并参考 Ztsdut/ml-architecture-diagram-skill。实际 clone 到 /workspace/ml-diagram-reference，commit 94b074e8f19de8b1be199343470fbd9a2b1bb3b4；读取完整 SKILL.md（补读被输出截断段）、style-guide、routing-and-layout、visual-grammar、semantic-review，检查 preview.svg 和 MIT LICENSE。该 checkout 未发现 AGENTS.md、未修改。按用户要求应用其中美术/路由部分，使用现有交互 IR；不复制代码/图形资产，不改为投稿输出工作流。引用与保留许可证见 references/visual-style.md、ml-diagram-reference-LICENSE.txt 和 THIRD_PARTY_NOTICES.md。

实施：新增 core/layout.ts，ELK layered 分层对齐后生成 ORTHOGONAL 端点/拐点，缓存完整布局。Cytoscape 使用显式端点+segments 重现实际路线，而非只设置视觉曲线属性；保持每条可见边及其证据。不允许拖动单个节点造成已计算路线失效，画布平移/缩放仍可用。白底、深灰细描边、小圆角、输入蓝/模块青/融合与输出绿/未解析浅金虚线；可进入用 ASCII [+] 避免离线字体缺字，更新图例。没有给未知模块补造结构。刷新教学与 Laya 页面。

实际验证：

- 初次 typecheck 报 Elk layout 推断类型不含 sections、corner-radius 类型不接受数值；添加 ElkNode 类型及 px 字符串后修复。最终 `npm run typecheck` 通过。
- `npm test`：20 passed（14 核心+3 展示+3 新布局）。覆盖 Laya 主流程与完整计算图、教学 Attention；路由完整、无斜线段、无穿越其他节点，拐点坐标转换复核，架构不变。未宣称所有任意密集图零交叉。
- `npm run build`、`.venv/bin/python scripts/demo.py`、`scripts/laya_regression.py`、`scripts/inspect_laya.py --repo /workspace/laya-source --root /workspace --out build/laya-repository`：成功。
- `MODEL_ATLAS_CHROMIUM=/usr/bin/chromium MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e`：7 passed（17.8 秒）；新增实际 Cytoscape source/segment/target 点检查，Laya 真实渲染无斜线。1366/1920 学习对比、边点击、原地展开、相机往返、源代码、安全导入均通过。报告 build/laya-diagnosis/playwright-orthogonal-full-results.json。HTTP 转发验证，非 file://。
- 最后导航字形改为 [+] 后，Laya 浏览器子集再次 3 passed；完整文件两个页面 `node build/laya-repository/check.mjs` passed，页面/控制台错误0、额外 HTTP 请求0。最终截图人工查看，直角线路与两个输出清晰，见 build/laya-repository/decision-preview.png。
- `npm run pack-skill` 更新工具包（含参考来源/许可证），`git diff --check` 无错误。Python 分析与模型未改，不重跑或新增运行验证。

恢复：先 npm run build；重建 demo/laya_regression/inspect_laya；npm test/typecheck；本地 HTTP 回归；pack-skill。布局样式不改变 unknown 形状和未解析 encoder 边界；没有上游 publication lint/论文导出、没有声称实际完整模型已运行。未提交或推送 GitHub。

## Model Atlas V2 增量改造（2026-10-12，中国标准时间）

完整读取用户上传的 23681 字节提示词并保存 MODEL_ATLAS_V2_UI_CODEX_PROMPT.md；检查现有 README/PROGRESS、SourceGraph/Session/Comparison Schema、Python 校验、展示投影、布局、前端与测试。继续遵循项目无 AGENTS.md 的现状；不修改另两个只读参考 checkout。实际技术栈 React 19.2.0 / Cytoscape 3.33.1 / ELK 0.11.0，未替换渲染引擎。

### 修改前基线

先复制旧单模型、双模型、Laya HTML 到 build/v2/before，再运行现有测试：Python 20 passed、TS 20 passed、浏览器 HTTP 转发 7 passed（16.6 秒）；报告分别为 before/pytest-results.xml、vitest-results.json、playwright-results.json。scripts/capture_v2_baseline.mjs 实际截图 1440×900 和 1920×1080：初始、选择、进入、诊断、双模型；浏览器 154.0.8037.57，页面错误0。不能把这些旧页面改为新版后再叫“修改前”。

开始时附件仅有提示词，已说明缺图。用户随后提供两张实际图片（第一张深色参考、第二张现状），已查看；又提供完整 drawio 与 SVG，作为格式数据检查而非指令或模型事实。drawio 141 个 style、140 个 sketch=1/jiggle=2，多数白色字体；SVG 2672×2010、1016 元素，未发现 script。样式提取保留 build/v2/reference/style-inspection.json；不复制水印/品牌，不把参考 Llama 两任务图导入本模型。采用文档规定的可读性 token，而非声称所有参数与原文件完全相同。

### 已实现范围

- 52px 单行应用栏；单模型不再标“左”；导航可收起、模块结构/当前计算分开、独立学习状态筛选；检查器默认关闭，选择后开启，可固定/调宽/关闭。诊断状态常驻，真实计数/口径/限制/完整配置在抽屉；错误仍醒目。源码和证据仍可查，空泛三段解释不再默认展示。
- 独立 core/scene.ts 教学区域；Laya 分组经源码审查、绑定完整源哈希，保留原始节点/源码范围/快照/依据，未知哈希降级结构分组。评分→Softmax→特征→act_head 依赖保留；每条展示边保留条件/端口/张量和原边ID；输入组可追溯具体八个来源。
- 聚焦、两级返回保持视口/选中/展开；旁侧展开保留父图，有随 pan/zoom/resize 同步的 UI 引用线。UI 引用只画在专用 SVG，不进入执行边/参数/差异。原地展开保留视口锚点，不强制 fit；仍可能使当前作用域其他节点重新排布，未声称实现完全局部布局。
- Rough.js 4.6.6 已评估后加到现有 Cytoscape 节点背景，不叠加不同步的节点 SVG 命中层。固定 ID seed、局部 SVG 缓存、斜线填充、文字净区；蓝复合模块/绿操作/黄输入输出/珊瑚虚线教学区，未知改灰色及 ? 标签。低缩放纹理淡化，正文/代码仍常规字体。第三方 MIT 和所有新增运行依赖许可证保留。
- ELK 分组布局：组内边的 container 局部坐标正确转为全局，新增端口附着检查，修复初次预览出现的脱节箭头；源码图不变。对比保持角色色、Δ 与未匹配单独标识、手动匹配/导出/导入/重算继续可用。

### 验证进度

首轮 typecheck 的 JSX 关闭括号及 Cytoscape 回调返回类型错误已修复。未知形状显示调整为需求文字“形状未确定”；对应旧字符串断言更新，不改事实。新分组/固定纹理/端口测试纳入 TS：25 passed。Python 再运行20 passed（0 skipped）。浏览器调整入口但保留已有业务断言，首轮 V2 全套10 passed（42.7秒）：原7项+2个桌面V2流程+键盘/reduced-motion/分组审计导出。截图 after/1440-*.png、1920-*.png 包括总览/选择/进入/旁侧展开/未知诊断/双图差异；原始 atlas-data 前后不变，双图同步选择、笔记往返、HTML 源码逃逸、加载后断网源码/对比、额外网络请求0均验证。

实际性能只记录布局+挂载耗时，不报告FPS。1440视口首轮：Laya 12节点/17边/3教学区约353ms；双图 Attention 各22节点/23边约393/435ms；缓存返回记录约31–62ms。环境浏览器报告5逻辑核、deviceMemory=16GB，未测GPU型号。记录 after/{1440,1920}-measurements.json，后续最终重跑将更新为实际新值。

当前正在最终截图/交互收尾与打包；最终结果追加在下方。file:// 仍受宿主管理策略阻止，本轮使用用户已授权的本地转发，不宣称 file:// 验收通过。缺少 Laya checkpoint/config 的解析边界继续保留；没有运行 Laya/权重下载或新模型事实。未提交/推送 GitHub。

### 最终交付与复核

最终细节修复：教学区标题靠左上，避免压住主流程；选中节点与分组在侧栏宽度变化时保持可见；正交线仅在拐点使用小圆角。保持原 React/Cytoscape/ELK 渲染器，新增 Rough.js 背景纹理。没有修改 SourceGraph 事实或 Schema 版本，历史快照/笔记键保持兼容。

实际最终命令与结果：

- `npm run typecheck` 通过；`npm test` 最终25 passed（3.59秒）；`.venv/bin/pytest` 20 passed、0 skipped。after/vitest-results.json 与 pytest-results.xml 保留。
- `npm run build`、`.venv/bin/python scripts/demo.py`、`scripts/laya_regression.py`、`scripts/inspect_laya.py --repo /workspace/laya-source --root /workspace --out build/laya-repository` 成功。
- `MODEL_ATLAS_CHROMIUM=/usr/bin/chromium MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e` 最终10 passed（41.3秒），报告 after/playwright-results.json。真实两级进入/返回、旁侧展开引用、人工匹配、笔记/导入、安全源码展示、加载后断网操作与原始架构不变均验证。截图实际来自1440×900和1920×1080；零页面/控制台错误、零额外网络请求。file://未验收。
- 最终布局+挂载：Laya 333.4/395.3ms；单图Block 133.9/139.2ms；Attention 264.9/250.7ms；缓存返回25–48ms。12步鼠标拖动画布210/225ms，不是FPS或模型推理耗时。详细记录 after/1440-measurements.json、1920-measurements.json。
- `npm run pack-skill`；`.venv/bin/pip wheel --no-deps --no-build-isolation dist/model-atlas --wheel-dir /tmp/model-atlas-v2-wheels` 成功。使用 /tmp/model-atlas-isolated/venv 安装 wheel，在 /tmp（脱离源码目录）实际 import 指向 site-packages；CLI validate 通过，build 生成2507554字节 HTML，确认包含真实 DecisionModel 数据、深色 token 和 Rough.js。初次 validate 误用了 --input，CLI 报错后改为位置参数并实际通过，不把报错算成功。
- `scripts/capture_v2_references.mjs` 从保留旧 HTML 补充 Laya 修改前截图。SVG 图片预览初次 decode 失败（about:blank 请求上下文），调整为先进入同源 HTTP 页面再加载；不影响已完成的模型页面验收。样式解析始终来自用户完整文件。
- `git diff --check` 无错误。未创建提交、推送或 PR。

交付：build/laya-repository/decision.html 与 attention.html（完整 Laya 文件静态分析）；build/mha.html、build/model_atlas_demo.html；build/v2/review.html 前后截图画廊及 before/after 原图/测试报告；dist/model-atlas-skill.zip 可安装分析/构建工具；dist/model-atlas-v2-review.zip 包含实际前端/Python源码、测试、文档、Schema、结构化数据、HTML 与前后截图（白名单打包，不包含环境、凭据或完整第三方仓库）。

限制：没有新增 Laya 动态 encoder/head 内部解析或真实 checkpoint 运行；未知尺寸仍未知。原地展开可能重排当前作用域，旁侧展开保持父图。教学分组可核查/导出，尚无任意分组编辑与导入界面。不宣称全部任意源码/超大密集图已覆盖。

恢复步骤：`npm ci`；`npm run typecheck && npm test && npm run build`；`.venv/bin/python scripts/demo.py`；完整 Laya 使用 inspect_laya.py 命令；按当前环境启动本地 HTTP 浏览器回归，再 pack-skill。旧 HTML 包含旧查看器，必须重新 build 或打开本轮生成文件才能看到 V2。

## GitHub 提交与推送（2026-10-12，Asia/Shanghai）

用户明确授权提交并推送。推送前检查 origin 为 https://github.com/Silhouette-my/LLM-study-panel.git，远端 main 为初始提交36f370f，与当前分支共同基线一致。源码、测试、文档、结构化数据、离线 HTML、前后截图及两个交付 ZIP 纳入提交；node_modules、虚拟环境、缓存和安装中间目录排除。沿用前轮实际通过的20 Python/25 TS/10浏览器结果，本轮无运行代码改动，不宣称重跑。执行 git diff --check，再创建提交并使用非强制 git push origin HEAD:main；推送结果以 git ls-remote 核对。

首次全量暂存检查报告生成的 minified JS/HTML 和第三方许可证尾部空白，未将该全量检查标为通过；对实际 core/web/tests/scripts/schemas/examples 与维护文档单独检查，无空白错误。保留生成资源原样，避免仅为格式改动已验证的离线包。提交后工作区干净。
