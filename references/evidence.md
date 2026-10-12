# 证据与覆盖规则

source：具体 AST 源码范围/注册事实。config：输入配置事实。static：从源码和配置推导，附假设与字段路径。teaching：通用教学解释，不代表作者动机。runtime：一次实际运行观察，仅该环境和输入。unknown：无法解析或无证据。

工具 analyze 的 executed 始终 false，证据不包含 runtime。项目 CPU 测试记录单独 build/runtime_observations.json，不将测试观察倒灌到静态架构中伪装运行分析。

教学适配器：resources/teaching.ast.sha256 与 examples/mini_decoder.py 的完整 AST 匹配。类结构/运算发生变化时降级；不能随意重写该指纹让未审查的模型套用旧 DSL。若扩展适配器，必须同步核对每个运算及参数，并更新形状、边界和运行测试。

通用路径：单类 forward，Linear/Embedding/LayerNorm/激活声明，构造器 with 内声明、显式 nn.Sequential，接收者链式调用、加法/乘法、torch.cat、tuple 输出和直接注册别名。未知输入 rank/shape 给原因；Linear 已知输出末维写入解释，不以末维假定完整 rank。ModuleList/循环/动态条件整体 opaque，保留源码和命名结果边界，继续提取后续语句；提前 return 后的依赖附带继续执行条件。条件候选注册和外部 encoder 不代表模块运行过。复杂共享与异构重复层只标未知，不猜测。
