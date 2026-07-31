[English](README.md) | **简体中文**

# UltraPlot Skill A/B 测试：相关性散点图

## 实验来源与隔离

- 两个条件分别在全新、无项目的 Codex 任务中生成，没有继承历史对话。
- 四项总体测试严格串行执行，每项使用独立任务目录和独立输入副本，不能读取
  已完成的其他测试。
- skill 禁用组不能读取任何 skill；skill 启用组可以读取 skill 指令，但生成时
  无法读取 skill 的 `examples/` 目录。
- 两个相关性条件收到内容逐字节相同的工作簿；所有生成任务结束后，产物才复制
  到当前示例目录。
- 唯一受控提示词因素是是否显式调用 `$ultraplot-figures`。

## 输入数据

- 工作簿：[multiple_data.xlsx](data/multiple_data.xlsx)
- 工作表与规模：`Sheet1`，4,305 行 × 32 个数值列
- 结构：4 种地类 × 4 种模型 × `_0`/`_1` 配对字段
- 地类：`cropland`、`forest`、`grassland`、`savanna`
- 模型：`DNN`、`GBRT`、`LR`、`SVR`
- 四种地类的完整配对数依次为 3,499、3,965、4,221、4,305；16 个地类/模型
  组合合计 63,960 个有限值配对

## 提示词控制

以下提示词根据仓库历史恢复。为避免暴露本机信息，输入文件使用仓库相对路径
表示。每组的完整有效提示词由对应的条件指令与下面的共同任务组成。

共同任务为：

> 绘图数据文件：`data/multiple_data.xlsx`
>
> 制作一张适合论文使用的相关性散点图，比较 cropland、forest、grassland 和
> savanna 四种地类中，DNN、GBRT、LR、SVR 四种模型下 `_0` 与 `_1` 的关系。
>
> 请提供可直接运行的 Python 代码，导出 PDF 和 PNG。

只有绘图指令发生变化：

| 条件 | 绘图指令 |
|---|---|
| 启用 skill | `请用 [$ultraplot-figures](../../SKILL.md) 制作图件。` |
| 禁用 skill | `请用 UltraPlot 制作图件。` |

## 图件对比

### 启用 skill

![skill 启用组相关性图](with_skill/correlation_scatter.png)

### 禁用 skill

![skill 禁用组相关性图](without_skill/correlation_scatter_ultraplot.png)

## 输出文件

| 产物 | 启用 skill | 禁用 skill |
|---|---|---|
| 分析与绘图 | [correlation_scatter.py](with_skill/correlation_scatter.py) | [correlation_scatter_ultraplot.py](without_skill/correlation_scatter_ultraplot.py) |
| PDF | [correlation_scatter.pdf](with_skill/correlation_scatter.pdf) | [correlation_scatter_ultraplot.pdf](without_skill/correlation_scatter_ultraplot.pdf) |
| PNG | [correlation_scatter.png](with_skill/correlation_scatter.png) | [correlation_scatter_ultraplot.png](without_skill/correlation_scatter_ultraplot.png) |

## 客观输出信息

| 项目 | 启用 skill | 禁用 skill |
|---|---:|---:|
| PDF 页数 | 1 | 1 |
| PDF 页面尺寸 | 182.9996 × 184.9787 mm | 191.7302 × 194.5358 mm |
| PNG 像素尺寸 | 7,204 × 7,282 px | 4,529 × 4,595 px |
| PNG 分辨率元数据 | 999.998 dpi | 599.999 dpi |
