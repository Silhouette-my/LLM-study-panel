# 图形与布局参考

这是 V1 的浅色图形参考记录。当前 V2 的深色手绘、未知灰色标识和教学长虚线规范见 v2-ui.md；不继续用 V1 的 unknown 虚线节点约定。

参考 [Ztsdut/ml-architecture-diagram-skill](https://github.com/Ztsdut/ml-architecture-diagram-skill)，读取版本 `94b074e8f19de8b1be199343470fbd9a2b1bb3b4` 的 SKILL.md、style-guide、visual-grammar、routing-and-layout、semantic-review 和 preview.svg。仅参考视觉规范，不复制其图形资产或解析/渲染代码。保留 MIT 许可证于 ml-diagram-reference-LICENSE.txt。

采用白色底、深灰细描边、紧凑小圆角及少量角色色：输入蓝、已声明模块浅青、合并/输出绿、未解析边界浅金和虚线。颜色附带标签/轮廓，不单独承载事实；不能因为采用 Attention 图形风格而给未知 encoder 虚构内部节点。可进入模块标注 [+]，避免离线字体缺失时导航符号显示为方框。

布局先由 ELK layered 计算节点，再用 ORTHOGONAL 生成完整端点与拐点；Cytoscape 显示同一条路线，不能只换一个 curve-style 却丢弃 ELK 的绕障路径。竖向层次适合当前狭长互动面板；同层对齐，分支保留，线段水平或垂直。节点固定以便已计算的路线保持有效；仍可拖动画布、缩放、聚焦/展开。

布局测试核对每条原始可见边都有路由、没有斜线段、不穿越其他节点，以及拐点的坐标转换正确。浏览器测试另核对真实渲染线段的方向，保留边点击、依赖高亮与源码定位。未宣称密集图零交叉，当前也未做投稿图片导出/上游 publication lint；参考技能用于互动页面中的美术和路由部分。
