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

共同任务是使用 UltraPlot 制作适合论文的相关性散点图，比较四种地类、四种模型
下 `_0` 与 `_1` 的关系，并提供可直接运行的 Python 代码以及 PDF、PNG。只有
以下绘图指令发生变化：

| 条件 | 绘图指令 |
|---|---|
| 启用 skill | `请用 [$ultraplot-figures](../../SKILL.md) 制作图件。` |
| 禁用 skill | `请用 UltraPlot 制作图件。` |

## 图件对比

| 启用 skill | 禁用 skill |
|:---:|:---:|
| ![skill 启用组相关性图](with_skill/correlation_scatter.png) | ![skill 禁用组相关性图](without_skill/correlation_scatter_ultraplot.png) |

## 输出文件

| 产物 | 启用 skill | 禁用 skill |
|---|---|---|
| 数据处理 | [process_data.py](with_skill/process_data.py) | 位于绘图脚本内 |
| 绘图 | [plot_correlation.py](with_skill/plot_correlation.py) | [plot_correlation_ultraplot.py](without_skill/plot_correlation_ultraplot.py) |
| PDF | [correlation_scatter.pdf](with_skill/correlation_scatter.pdf) | [correlation_scatter_ultraplot.pdf](without_skill/correlation_scatter_ultraplot.pdf) |
| PNG | [correlation_scatter.png](with_skill/correlation_scatter.png) | [correlation_scatter_ultraplot.png](without_skill/correlation_scatter_ultraplot.png) |
| 处理后配对数据 | [processed_pairs.csv](with_skill/processed_pairs.csv) | 不单独写出 |
| 统计量 | [correlation_statistics.csv](with_skill/correlation_statistics.csv) | 由绘图脚本在内存中计算 |
| 排除汇总 | [exclusion_summary.csv](with_skill/exclusion_summary.csv) | 不单独写出 |

## 客观输出信息

| 项目 | 启用 skill | 禁用 skill |
|---|---:|---:|
| PDF 页数 | 1 | 1 |
| PDF 页面尺寸 | 182.9996 × 189.8647 mm | 209.5500 × 218.4400 mm |
| PNG 像素尺寸 | 7,204 × 7,474 px | 3,300 × 3,440 px |
| PNG 分辨率元数据 | 999.998 dpi | 399.999 dpi |
