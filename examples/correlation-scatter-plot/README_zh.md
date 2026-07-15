[English](README.md) | **简体中文**

# `ultraplot-figures` 科研绘图对比：预测值与真实值关系

本案例使用同一份 Excel 数据和同一条科研绘图提示词，对比允许使用
`$ultraplot-figures` 与不使用任何 skill 两种条件下生成的图件和脚本。

## 测试设置

| 条件 | 使用 skill | 不使用 skill |
|---|---|---|
| Skill 设置 | 只允许 `$ultraplot-figures`，不得使用其他 skill | 不允许使用任何 skill，也不得读取 skill 文件或 helper |
| 绘图库设置 | 由 `$ultraplot-figures` 的规则决定 | 优先使用 UltraPlot，其他普通 Python 库也可直接使用 |
| 输入数据 | 同一份 XLSX | 同一份 XLSX |
| 科研绘图提示词 | 完全相同 | 完全相同 |
| 生成模型与客户端 | `GPT-5.6 sol`，Codex Desktop for Windows | `GPT-5.6 sol`，Codex Desktop for Windows |

两个分支在共同科研绘图提示词之前分别收到以下设置：

- 使用 skill：`请只使用 $ultraplot-figures，不要使用包括 xlsx 在内的其他任何 skill。`
- 不使用 skill：`请不要使用任何 skill，也不得读取任何 skill 的 SKILL.md、references、scripts 或 helper。UltraPlot 库优先使用，其他普通 Python 库也可以直接使用。`

- 数据：[四类土地与四种模型的预测数据](data/multiple_data.xlsx)
- 工作表：`Sheet1`，共 4,305 行和 32 个数值列
- 字段：`_0` 表示真实值，`_1` 表示对应的预测值

两组图件的设计、布局和视觉编码均由模型完成，图件生成后未进行二次视觉设计或数据
修改。为便于公开使用，脚本中的本地文件路径已替换为仓库相对路径，并从交付脚本中
移除内部 QA 脚手架；这些代码整理没有改变图形内容。

## 共同提示词

> 请根据下面的数据制作一张适合科研论文使用的预测值与真实值关系图件：
>
> 数据文件：`data/multiple_data.xlsx`
>
> 数据用于比较 cropland、forest、grassland 和 savanna 四种土地类型下 LR、SVR、GBRT 和 DNN 模型的预测效果。每组列名中的 _0 表示真实值，_1 表示对应的预测值。
>
> 我希望图中能够完整展示不同土地类型和模型组合中预测值与真实值的一致性，让读者直观比较各模型在不同土地类型下的预测表现、误差特征和可能的系统偏差。
>
> 请先检查工作簿内容，再根据数据特点选择合适的图形、布局、视觉编码和统计标注。请正确处理缺失值；如果数据没有提供响应变量名称或单位，不要自行猜测。请保持科学表达谨慎，不要作超出这些预测值与真实值配对数据支持范围的推断。
>
> 请提供可编辑、可独立运行的 Python 绘图脚本，以及 PDF 和高分辨率 TIFF 图件。

## 图件对比

| 使用 `$ultraplot-figures` | 不使用任何 skill |
|:---:|:---:|
| ![使用 ultraplot-figures 生成的科研图件](assets/with_skill.png) | ![不使用 skill 生成的科研图件](assets/without_skill.png) |

两张预览均由各自最终 TIFF 在白色背景上缩放至 1,400 px 等宽生成，保持原始纵横比，没有裁切、调色或重新排版。

## 输出文件

| 文件 | 使用 `$ultraplot-figures` | 不使用任何 skill |
|---|---|---|
| Python 脚本 | [prediction_vs_observed_ultraplot.py](with_skill/prediction_vs_observed_ultraplot.py) | [plot_prediction_vs_observed.py](without_skill/plot_prediction_vs_observed.py) |
| PDF | [prediction_vs_observed.pdf](with_skill/prediction_vs_observed.pdf) | [prediction_vs_observed_4x4.pdf](without_skill/prediction_vs_observed_4x4.pdf) |
| TIFF | [prediction_vs_observed.tif](with_skill/prediction_vs_observed.tif) | [prediction_vs_observed_4x4.tiff](without_skill/prediction_vs_observed_4x4.tiff) |

## 客观文件信息

| 项目 | 使用 `$ultraplot-figures` | 不使用任何 skill |
|---|---:|---:|
| PDF 页数 | 1 | 1 |
| PDF 页面尺寸 | 183.00 × 165.64 mm | 208.91 × 207.76 mm |
| PDF 字体 | 2 个字体，全部嵌入；无 Type 3 | 3 个字体，全部嵌入；均为 Type 3 |
| PDF 内嵌栅格 | 16 个，最低有效分辨率 600 dpi | 16 个，最低有效分辨率 600 dpi |
| TIFF 像素尺寸 | 4,322 × 3,912 px | 4,934 × 4,907 px |
| TIFF 分辨率 | 600 dpi | 600 dpi |
| TIFF 色彩模式 | RGB，无 alpha | RGB，无 alpha |
| TIFF 压缩 | LZW | LZW |
| 脚本行数 | 370 | 371 |

## 阅读说明

两种条件分别选择数据层、统计标注、布局和视觉编码，因此这些差异属于案例结果的一部分。
科研图件和代码仍需由研究者结合变量含义、数据来源和投稿要求审核。
