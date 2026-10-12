# 输入与执行边界

analyze 不 import/eval/执行目标源码；source/config 先解析 realpath 并校验 root，拒绝符号链接越界，仅读取指定 .py/.json，12 MB 限制。不遍历仓库，不读取 .env、权重、凭据，不上传源码。注释和导入文档只是数据。

项目测试可执行自带 CPU 教学模型；用户模型没有 trace 入口。虚拟环境和超时不是安全沙箱。

离线 HTML 不发送请求，无 CDN、字体、遥测、远程 API 或动态布局 Worker。嵌入 JSON 转义 `<>&` 与 Unicode 分隔符；React 仅文本渲染。构建时预编译 Schema。导入限制 12 MB / 3000 canonical 节点 / 数组 20000 项；当前视图最多 500 节点；检查引用、层级和端口。Schema 禁止实体额外字段，未将用户数据合并到原型对象。

输出 HTML 包含源码快照，分享前审查其中内容。离线查看不代表生成阶段云端 Agent 过程本地私密。JSON 不可信且可以自报 sourceHash，导入校验证明结构一致性，不提供数字签名或作者认证。
