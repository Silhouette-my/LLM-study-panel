# Laya 完整仓库核对

核对对象：NandhaKishorM/laya，commit `c4a805b5160621bbfc53417126990a67d3163bc5`。读取源码，不导入 Laya、不加载权重。

`laya/common.py` SHA-256 为 `f8e4c7408fb72e4088f4ac6db3c6764b387a955aea978e8360e0c189615a9505`，与用户上传 HTML 的原文件哈希完全一致。首个 if 截断及 with 内声明遗漏不是版本差异。此前只能恢复片段；现在已经核对完整文件。

## 实际结构和配置来源

- DecisionModel（574–658）：外部 encoder → 加 qtype embedding → 可选 TransformerEncoder head → 按 marker_pos gather → scorer 输出 logits；另用首 token 的 pooled 表示及四个置信度特征 → act_head 输出 act_logits。
- build_model（693–716）：`head_layers = cfg.get('head_layers', 2)`，`n_act = len(cfg.get('act_costs', {})) + 1`；AutoConfig/AutoModel 根据 `encoder_dir` 或 `cfg['encoder']` 创建 backbone。构造器的 n_act 默认 2 不能替代这里的真实配置推导。
- agent.py（611 起）加载 checkpoint 的 `rl_agent_config.json`；不是源码仓库根目录的配置文件。encoder 的 `config.json` 也由 checkpoint 或模型提供。
- verify/checkpoints.json 列出 english/typed-decisions 为 ModernBERT-large，multilingual 为 mmBERT-base。这是仓库声明，不足以认定用户本地使用的模型。
- head 用 `nhead=max(1,d//64)`，FFN 宽度 `4*d`，norm_first=True，默认 ReLU；其 head 数不应直接使用 backbone 的 head 数。
- _DynamicMultiheadAttention（505–556）替换 head self_attn，继承 nn.MultiheadAttention。显式快速路径有 packed QKV（同一对象）与分开投影分支、head 维拆分、mask、scaled_dot_product_attention、拼接和 out_proj；满足 fallback 条件时调用 super().forward。它不是整个 backbone 的 Attention，也不是 GQA 教学适配器。
- parallel_option_masks（329 起）决定并行 option 布局时的 encoder mask；不能用普通 causal decoder 掩码替代。源码上下文 JSON 保存该函数，但未声称已提取函数内部图。

## 有条件的静态形状解释

若输入契约为 input_ids/attention_mask `[B,T]`、qtype `[B]`、marker_pos/marker_mask `[B,M]`，encoder 输出 `[B,T,d]`，则 scorer 输入 `[B,M,d]`、logits `[B,M]`；首 token pooled `[B,d]`、四个特征 `[B,4]`、act_head 输入 `[B,d+4]`、输出 `[B,A]`。这是根据源码及上述明确假设的人工静态解释，不是 runtime 观察；这些契约未写入当前通用提取图，未知完整形状仍为 null。

按 PyTorch 默认带 bias 的 TransformerEncoderLayer/MultiheadAttention 参数语义，每个 decision head 层理论参数为 `12*d*d+13*d`；type_emb 为 `3*d`，scorer 为 `d*d+4*d+1`，act_head 为 `256*d+1280+257*A`。当确认为 L 层、这些默认语义未改动时，encoder 之外理论合计 `L*(12*d*d+13*d)+d*d+263*d+1281+257*A`。不包含 encoder，不是当前工具已确认的参数实体或运行统计；没有实际 d/L/A 就不代入数值。模型源码未实现持久 KV cache，不能把理论存储推导说成缓存占用实测。

## 当前交付与剩余工作

完整文件重新分析：DecisionModel 67 节点、77 边、3 scopes、12 声明实例；scorer/act_head 可进入，两个输出保留。自定义 Attention 34 节点、47 边、1 scope；控制分支仍 opaque，继承的参数/模块也未被展开。两份文档 parameterCount=null、executed=false。

Attention 页面是独立源码分析，尚未链接为 DecisionModel 中 head 的可进入子作用域。不能宣称完整模型 → head → Attention 的三级浏览已支持。进一步实现它需要显式源码/库适配、实际 checkpoint 与 encoder/config，以及有意义的形状/参数验证；generic 单文件提取不会自动完成此事。

可复现命令（完整仓库与输出均在允许根目录内）：

```
python scripts/inspect_laya.py --repo /workspace/laya-source --root /workspace --out build/laya-repository
```

输出 decision.html、attention.html、两份 architecture/report 和 source-context.json（源码上下文、commit、哈希、工作树是否修改）。可用 `--config` 明确传入实际分析配置；不传时写入空配置并标注未知，不选择默认 checkpoint。构建无需安装或执行 Laya。工具包包含该脚本，但不包含第三方完整仓库。
