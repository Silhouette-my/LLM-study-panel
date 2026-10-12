# _DynamicMultiheadAttention 分析报告

快照：7b6ba39f74db8098a11c2d0b1812e3b20a8a54b3efe52efd11b114ba49166d5d
模式：静态 AST；未执行目标源码；无运行验证。
覆盖：局部静态提取（非完整架构）；可进入模块 0；未解析计算/结果边界 21。
节点：34；独立参数实体：0；参数数：None。
证据：{"source": 34, "config": 0, "static": 3, "unknown": 31, "runtime": 0}

覆盖与未知：
- 动态控制流/循环：内部 opaque，保留变量出口并继续读取后续源码；未选择路径或枚举重复层
- 动态控制流/循环：内部 opaque，保留变量出口并继续读取后续源码；未选择路径或枚举重复层
- 动态控制流/循环：内部 opaque，保留变量出口并继续读取后续源码；未选择路径或枚举重复层
- 动态控制流/循环：内部 opaque，保留变量出口并继续读取后续源码；未选择路径或枚举重复层
- 动态控制流/循环：内部 opaque，保留变量出口并继续读取后续源码；未选择路径或枚举重复层
- 不支持表达式，保留真实输入边界: is_causal and mask is None
- 不支持表达式，保留真实输入边界: self.dropout if self.training else 0.0
- 不支持表达式，保留真实输入边界: F.scaled_dot_product_attention(q, k, v, attn_mask=mask, is_causal=is_causal and mask is None, dropout_p=self.dropout if self.training else 0.0)
- 不支持表达式，保留真实输入边界: attn.permute(2, 0, 1, 3)
- 不支持表达式，保留真实输入边界: attn.permute(2, 0, 1, 3).flatten(-2)
- 动态控制流/循环：内部 opaque，保留变量出口并继续读取后续源码；未选择路径或枚举重复层
- 不支持表达式，保留真实输入边界: self.out_proj(attn)
- 通用 AST 局部提取：条件/循环内部不展开；继续保留后续计算和多输出。仅直接声明的 nn.Sequential 可进入。外部注入模块、未知尺寸、共享及训练条件不作运行验证或参数估算。
