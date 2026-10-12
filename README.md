# Model Atlas · 模型学习图谱

从真实 PyTorch 单文件源码与 JSON 配置生成可双击打开的离线学习 HTML。这个仓库的教学 Decoder 是小型教学实现，不是官方 LLaMA 复现，不兼容官方权重。默认不下载权重、不需要 GPU、不执行输入源码。

现有两个闭环：整体 → 第 i 个 Decoder Block → Attention / Gated MLP；源码、张量、证据、学习状态与笔记联动。MHA/GQA 双栏对比支持联动聚焦、建议接受/拒绝、一对多/多对一人工修正及差异重算、JSON 导入导出。

通用模型默认显示“主流程”，将辅助计算作为视图汇总；切换“计算细节”恢复全部原始节点。汇总不创建新模块或运行事件，组成节点可在右侧查看并定位源码。未知张量形状显示“形状未确认”，连线不重复标注 null；配置与分析限制按需展开。补充配置不保证动态分支形状可解析，未支持的形状传播仍保留未知。

V2 使用深紫黑画布、彩色手绘描边、稀疏斜线填充与珊瑚色教学区域。界面外壳保持常规字体；未知节点以灰色和 `? 未解析` 标记，可进入模块标注 `[+]`。节点纹理由固定 ID seed 的 Rough.js 生成并内联，Cytoscape 命中/缩放与 ELK 布局继续保留。来源分组、渲染决策和边界见 references/v2-ui.md。

## 打开交付

- `build/mha.html`：单模型学习包。
- `build/model_atlas_demo.html`：双模型离线演示，直接用桌面浏览器打开，地址为 file://。
- `build/{mha,gqa}.architecture.json`、对应 `.report.md`：静态结构及分析覆盖报告。
- `build/mha_vs_gqa.comparison.json`：建议对应关系、配置/形状/参数/拓扑差异与理论缓存量。
- `build/runtime_observations.json`：独立 CPU 测试观察，不能当成 analyze 的执行证据。

学习包包含源码片段，分享前审查。离线页面无 HTTP(S) 依赖；生成阶段使用云端 Agent 不代表整个流程本地私密。

## 安装与完整构建

实际验证版本：Python 3.12.14、Node 24.19.0（最低 22）、npm 11.9.0。Python >=3.11；运行 compare/build/validate 同时需要 Node。基本分析不需要 PyTorch。npm package-lock.json 锁定前端依赖；requirements.lock 记录本次测试环境，包含可选 CPU PyTorch。

```bash
cd /workspace/LLM-study-panel
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
npm ci --cache /tmp/model-atlas-npm
npm run demo
```

`npm run demo` 构建固定查看器，再运行两次 analyze、三次 validate、compare、单模型和双模型 build。所有 out 自动创建父目录。资源位置使用 Python 包资源，不依赖绝对开发路径。

```bash
model-atlas analyze --source examples/mini_decoder.py --entry MiniDecoder \
  --config examples/configs/mha.json --out build/mha.architecture.json
model-atlas analyze --source examples/mini_decoder.py --entry MiniDecoder \
  --config examples/configs/gqa.json --out build/gqa.architecture.json
model-atlas validate build/mha.architecture.json
model-atlas compare --left build/mha.architecture.json \
  --right build/gqa.architecture.json --out build/mha_vs_gqa.comparison.json
model-atlas build --input build/mha.architecture.json --out build/mha.html
model-atlas build --input build/mha.architecture.json --input build/gqa.architecture.json \
  --comparison build/mha_vs_gqa.comparison.json --out build/model_atlas_demo.html
```

`validate` 支持 architecture、comparison、session；build 与页面导入额外检查跨文档引用/快照。失败返回非零和可定位错误，不写空成功输出。`--root` 默认当前目录，拒绝路径/符号链接越界。

## 分析自己的受支持模型

```bash
model-atlas analyze --root /path/to/project --source /path/to/project/model.py \
  --entry MyModel --config /path/to/project/config.json --out build/my.architecture.json
model-atlas validate build/my.architecture.json
model-atlas build --input build/my.architecture.json --out build/my.html
```

完整三级教学适配器仅接受 examples/mini_decoder.py 的整个 AST 指纹；注释/空白变化允许，任何代码结构改动降级。通用 AST 路径不依赖文件名或内置类名，支持 Linear/Embedding/LayerNorm/激活声明、构造器 with 内声明、显式位置参数 nn.Sequential、直接 forward 调用、链式接收者调用、残差加法、乘法、torch.cat、多输出及直接参数别名共享。输入 rank/尺寸未知时不假设二维或三维；已知 Linear 输出末维在说明中记录，完整 shape 保留未知。复杂自定义模块、跨文件导入、循环、ModuleList、动态条件整体 opaque，保留源码和边界，并继续提取后续语句；条件结果不是某条分支的运行结果。外部注入 encoder 只有声明，不能自动获得其内部结构。先读 `.report.md` 和页面覆盖提示，不要把局部图当成完整解析。

静态注册树与调用图独立。注册未调用模块只计入参数，不进入执行图。教学重复层全部保留独立实例，提供逐层查看与已检查的同结构/独立参数标签；通用异构重复层不共用模板。参数总数无法确认时为 null。

Laya 回归样例来自用户提供 HTML 的 DecisionModel 源码片段，不是完整仓库。开发环境运行 `.venv/bin/python scripts/laya_regression.py` 可重建原快照查看器及修复后的局部分析；浏览器回归测试还需先运行教学 demo 和 pytest 生成各测试文件。源码片段不执行，encoder 与动态 head 内部仍未解析。

有完整 Laya checkout 时，运行 `python scripts/inspect_laya.py --repo /workspace/laya-source --root /workspace --out build/laya-repository`，从实际 common.py 构建 DecisionModel 与自定义 Attention 两份独立页面，并保存构建函数/并行 mask 的源码上下文、文件哈希与 Git 版本。可传 `--config` 提供实际分析配置；省略表示配置未知。这不会自动选择 checkpoint 或展开 transformers encoder，也不会将源码上下文标成运行结果。

## 离线操作

打开单模型后，检查器默认关闭。点击节点查看详情；“进入模块”聚焦，“旁侧展开”保留父图查看子图，珊瑚色“展开视图 · UI 引用”不是执行依赖；“原地展开一级”展示真实子边界。面包屑或“返回父级”恢复每级选中、展开、缩放和位置。画布可拖动、缩放和适配；未知模块只提供边界/源码入口。

导航默认显示模块声明树，声明与静态调用分开标注；切换“当前视图计算”查看算子。搜索支持名称、角色、类名、源码路径；Ctrl/Cmd+K 打开搜索，输入区域不触发全局快捷键。学习筛选单独选择。检查器可固定、关闭、拖动左边缘调宽，也可键盘调宽。辅助“节点与教学分组”列表默认收起，可键盘打开和选择节点。

右侧“讲解/张量/源码/笔记”。点击图边看原始张量、具体输入端口和条件；上游/下游高亮仅当前范围，跨层由显式端口绑定解释。“视图”菜单开启教学步进/张量标注，默认不会摆出所有专用工具。步进是依赖层，不是运行回放。源码是生成时快照，行号不一定等于当前磁盘内容。常驻“静态/局部静态 · 未运行验证”入口打开诊断抽屉，显示完整限制与真实统计口径，不因美化消除未知。

双模型打开后默认对比，导航与检查器收起。选择和进入匹配子作用域时联动；没有唯一匹配则不强行定位。“差异与匹配”抽屉保留逐项差异、接受/拒绝候选和多选人工重算；Δ 和未匹配标识不覆盖角色色，也不证明等价。导出 ComparisonDocument，导入时核对两侧 snapshot；拒绝不匹配版本。

笔记保存独立 SessionDocument，可显式 JSON 导出/导入。本地缓存只提供便利，file:// 不支持缓存时导出仍有效。重新生成不会写入个人 session；旧快照笔记保留 pending，未自动猜测跨版本关联。导入 JSON 可替换当前活动侧架构，不导入/分析 Python。导入 12 MB、3000 节点限制；当前图最多 500 节点。

“更多”提供导入、导出笔记/匹配/架构与分组来源审计。架构与 HTML 包含源码；笔记格式仍为原 schema 1.0。V2 未改分析器版本或已有事实 Schema，同一源码/配置的快照和锚点保持兼容；不覆盖用户文件。教学分组导出供审计，本轮未提供任意分组编辑/导入。

V2 实际前后截图与验证记录在 build/v2/{before,after}，覆盖 1440×900 和 1920×1080 的总览、选择、进入、旁侧、未知诊断与双图差异。SOURCE 结构仍不含这些视觉状态。原地展开可能重排当前作用域，视口锚点会保留；需要完全保留父图时使用旁侧展开。

## MHA / GQA 的证据口径

hidden_size=64，heads=8，head_dim=8，kv_heads 8 → 2。Q 输出 8×8=64；K/V 输出 kv_heads×8：64 → 16。K/V 分头后 [B,8,T,8] → [B,2,T,8]，源码 repeat_interleave 后均为 [B,8,T,8]，页面单独展示投影、reshape、transpose、复制。

无 bias 的 K/V 线性参数为 2×hidden_size×kv_heads×head_dim。单层减少 2×64×(8−2)×8=6144，两层 12288。完整参数 MHA=98624、GQA=86336，独立参数口径，无 embedding/head 共享。

理论缓存：2×layers×B×T_cache×kv_heads×head_dim×bytes_per_element，假设未复制 KV 存储、B=2、T_cache=4、float32=4 bytes，则 8192 → 2048 bytes，比例 1/4。这是理论估算，未测量；示例没有实际 cache，不推导速度或真实显存收益。

## 测试

```bash
source .venv/bin/activate
pip install torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu
pytest -q --junitxml=build/pytest-results.xml
npm run typecheck
npm test
# 已安装的系统 Chromium（本次验证：154.0.8037.57）
MODEL_ATLAS_CHROMIUM=/usr/bin/chromium npm run test:e2e
# 其他环境可安装 Playwright 浏览器，再不指定 MODEL_ATLAS_CHROMIUM
npx playwright install chromium
npm run test:e2e
```

PyTorch 仅 CPU 测试需要：固定 seed=2026、float32、eval、输入 [2,4]，输出与投影/复制前后尺寸、独立参数差得到运行验证。缺少 PyTorch 会明确 skip。测试仅执行本项目教学模型；任意用户模型没有 trace 命令。

测试报告存入 build；file:// 检查两个桌面尺寸的功能、控制台、无 HTTP(S) 请求及恶意/非法导入，截图只是辅助证据。运行环境限制和确切结果见 PROGRESS.md。

## Skill 打包与本地使用

```bash
npm run pack-skill
# 得到 dist/model-atlas/ 与 dist/model-atlas-skill.zip
python -m venv /tmp/atlas-skill-venv
/tmp/atlas-skill-venv/bin/pip install ./dist/model-atlas
cd dist/model-atlas
/tmp/atlas-skill-venv/bin/python scripts/demo.py
```

自包含 Skill 包携带 SKILL.md、Python 工具、Schema、参考资料、教学输入和已编译资源，无 node_modules/.venv/密钥/权重。首次 pip 安装需要依赖源或预先缓存的依赖；生成 compare/build 需要本机 Node，单文件 HTML 查看不需要 Node/Python。打包结果在独立临时目录经过安装及全流程验证，见 PROGRESS。

当前宿主是 Codex 桌面，技能可能通过受管插件而非本地目录加载；这里不擅自修改全局配置。对启用本地技能目录的 Codex CLI，可将解压后的 model-atlas 目录放到已配置的 `$CODEX_HOME/skills/model-atlas`（常见默认 `~/.codex/skills/model-atlas`），重启/重新加载后核对技能列表。其他宿主按其实际 Skill 安装机制导入。未在本会话激活新 Skill，也不宣称所有产品支持相同安装目录。当前可直接要求 Agent 阅读本仓库 SKILL.md 并使用 CLI。

## 已知边界

静态单文件分析；未知控制流不展开；不同家族自动对应不承诺；人工分组也不是计算等价证明。没有 RoPE、真实 cache、执行回放、激活/注意力数值、性能排名、在线聊天、任意模型运行采样。详见 DESIGN.md、SECURITY.md 与 references/evidence.md。

当前宿主禁止 file:// 导航时，可按本次已验证的本地转发方式继续使用同一单文件 HTML：

```bash
python -m http.server 8787 --bind 127.0.0.1 --directory build
# 打开 http://127.0.0.1:8787/model_atlas_demo.html
# 本地 HTTP 浏览器功能测试；不是 file:// 验证
MODEL_ATLAS_CHROMIUM=/usr/bin/chromium MODEL_ATLAS_E2E_HTTP=1 npm run test:e2e
```

本次 file:// 验证被 Chromium 的宿主管理策略阻止，保留失败记录；本地转发模式 1366×768 / 1920×1080 的真实交互验证通过。测试只允许启动 HTML 的主文档请求，不存在额外 HTTP(S) 资源请求。`pytest` 先生成初始注入安全测试用的 attack-fixture.html，再运行浏览器测试。
