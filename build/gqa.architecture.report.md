# MiniDecoder 分析报告

快照：ded4bd7d8fef7c96c91246a0116dd963b37b1deb5c3ff88949ca8fb0f936638a
模式：静态 AST；未执行目标源码；无运行验证。
覆盖：受支持教学适配器；可进入模块 6；未解析计算/结果边界 0。
节点：81；独立参数实体：21；参数数：86336。
证据：{"source": 81, "config": 8, "static": 102, "unknown": 0, "runtime": 0}

覆盖与未知：
- 教学适配器：完整 AST 指纹匹配；分头链拆为源码子运算。无 RoPE、KV cache、性能测量。未运行目标源码。
