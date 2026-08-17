[English](README.md) | **简体中文**

# UltraPlot Figures

> 使用 UltraPlot 制作可复现、符合出版尺寸要求的静态科研图件。

`ultraplot-figures` 用于制作和修改静态科研图件，也可协助排查绘图问题、审阅图件并
核验输出。使用时，请提供绘图数据，并说明图件所对应的科学问题和作图目的；如有
版面尺寸、输出格式或期刊要求，也请一并说明。输出包括可复现、便于继续修改的
Python 绘图脚本及相应的渲染结果。

本仓库是一个 **Codex skill**，不是
[UltraPlot](https://github.com/ultraplot/ultraplot) Python 包，也不是独立绘图软件。

## v1.2.0 更新内容

v1.2.0 调整了默认样式策略：

- 将 UltraPlot 的当前有效配置作为视觉样式的默认依据。
- 仅在科学含义、出版规格或使用最终数据渲染后发现具体问题时，覆盖相应的视觉参数。
- 在相关图件中复用已经确定的分类颜色映射，同时避免为只在单张图中出现的分类建立
  不必要的映射。
- 将内置[绘图示例](references/recipes.md)保持为简洁的科学编码与 API 框架，默认继承
  UltraPlot 的当前有效视觉设置。

> [!CAUTION]
> **本 skill 生成或修改的科研图件，在投稿或正式发布前必须由作者复核。** 本 skill
> 提供可复现、便于修改的 Python 绘图代码和对应成图，以减少从头编写绘图代码的
> 工作。图件的科学表达和具体细节仍需作者结合研究内容和投稿要求作最终检查与调整。

## 快速开始

在 Codex 中调用 `$ultraplot-figures`。制作或重新绘制图件时，请提供绘图数据；修改
已有图件时，尽量同时提供原绘图脚本；只需检查现有成图时，可以直接提供 PDF 或
PNG。请说明科学问题和作图目的，并附上已有的版面尺寸、输出格式或期刊要求。

```text
请使用 $ultraplot-figures。
输入：[绘图数据、已有绘图脚本、PDF 或 PNG]
科学问题：[图件需要回答的问题]
作图目的：[图件需要说明的内容]
输出要求：[可选的尺寸、格式或期刊要求]
```

### 默认设置

没有指定版面尺寸时，使用 UltraPlot 的 `nat2` 预设，即 183 mm 总宽度。除非另有
要求，输出 PDF 和 PNG。

没有指定期刊或字体时，UltraPlot 默认使用 9 pt 无衬线 TeX Gyre Heros。它是开源的
Helvetica 风格字体，在小尺寸图件中较清楚，也便于跨系统复现。它符合许多期刊常见的
无衬线风格。例如，[Nature 要求图中文字使用无衬线字体，并优先推荐 Helvetica 或 Arial](https://www.nature.com/nature/for-authors/final-submission)。

对于中文文本，本 skill 保留 TeX Gyre Heros 作为拉丁字符主字体，并将
`Microsoft YaHei`（微软雅黑）作为默认中文回退字体。微软雅黑是无衬线中文字体，覆盖
常用简体中文字形，在科研图件常见的小字号下笔画清楚、易于辨认。

### 请求示例

```text
请使用 $ultraplot-figures 根据 results.csv 制图，比较各处理组与对照组的时间变化
和不确定性。图件用于展示各组的变化趋势及差异。请返回简洁、便于维护的绘图脚本、
PDF 和 PNG，并在回复中概述重要核验问题。
```

## 安装

### 1. 让 Codex 安装本 skill

将下面这段请求发送给 Codex：

```text
请使用 $skill-installer 从 https://github.com/lwq-star/ultraplot-figures 安装
ultraplot-figures。该 skill 位于仓库根目录（路径 `.`），安装名称使用
`ultraplot-figures`。
```

安装完成后，可在下一轮使用 `$ultraplot-figures`。如果 Codex 尚未识别新 skill，
请新建一个任务后再调用。

### 2. 安装 UltraPlot

使用 pip 安装：

```bash
pip install ultraplot
```

也可以使用 conda：

```bash
conda install -c conda-forge ultraplot
```

需要地理投影时应另行安装 Cartopy；其他数据读取和处理库按具体任务安装。详细要求
见 UltraPlot [安装指南](https://ultraplot.readthedocs.io/en/stable/install.html)。

安装本 skill 不会自动安装 UltraPlot 或其依赖。

本 skill 在使用时至多每天检查一次 GitHub 上的最新稳定版，但不会自动下载、安装
或替换文件。设置 `ULTRAPLOT_FIGURES_UPDATE_CHECK=0` 可以关闭检查。

## 交付物与使用限制

有数据或绘图源文件时，Codex 只会根据任务需要保留：

- 简洁、可独立运行、便于继续修改的绘图代码；
- 需要实质性数据处理时使用的预处理代码，以及绘图实际使用的最终处理结果；
- 用户要求的最终图件；未指定格式时默认保留 PDF 和 PNG。

Codex 在内部完成核验，不保留核验代码、独立核验说明、manifest、诊断图、日志、
中间数据、排除记录表或其他仅用于检查的文件。重要假设和未解决问题在最终回复中概述。

只有 PDF 或栅格图片时，本 skill 只能检查可见内容和文件信息，不能从成图还原未提供
的数据、处理流程、统计方法或可复现代码。

本 skill 默认制作 Python 静态图件，不用于交互式 dashboard 或网页应用，也不支持
生成流程图。

## 示例

完整示例独立维护在
[`ultraplot-figures-examples`](https://github.com/lwq-star/ultraplot-figures-examples)
仓库中，因此安装本 skill 时不会下载示例数据或渲染结果。

- [2025 年全球 M5+ 地震 skill 对照案例](https://github.com/lwq-star/ultraplot-figures-examples/blob/v1.0.0/examples/earthquake/README_zh.md)：
  在相同数据和提示词下，分别使用和不使用 `$ultraplot-figures` 生成图件。案例包含
  输入数据、必要的可编辑脚本及最终 PDF 和 PNG。
- [预测值与真实值模型对照案例](https://github.com/lwq-star/ultraplot-figures-examples/blob/v1.0.0/examples/correlation-scatter-plot/README_zh.md)：
  使用相同 Excel 数据和提示词，对比 LR、SVR、GBRT 和 DNN 在四种地类下的图件。
  案例包含输入数据、必要的可编辑脚本及最终 PDF 和 PNG。

## 反馈与联系

欢迎反馈 bug、使用体验和改进建议。如果遇到报错、说明不清或输出异常，请优先在
[GitHub Issues](https://github.com/lwq-star/ultraplot-figures/issues) 反馈。条件允许
时，请附上 Python 与 UltraPlot 版本、相关提示词或脚本、最小可复现示例及完整报错
信息。

如不便公开反馈，也可以发送邮件至
[laiwenqinstar@gmail.com](mailto:laiwenqinstar@gmail.com)。请勿在 Issue 或邮件中
提供密码、API 密钥、机密数据或其他敏感信息。

## 致谢

本 skill 基于开源 [UltraPlot](https://github.com/ultraplot/ultraplot) 项目构建。
感谢 UltraPlot 的维护者与贡献者开发并开放这一科研绘图库，为本工作流程提供基础。

根据 UltraPlot 维护者在
[cvanelteren/ultraplot-figures](https://github.com/cvanelteren/ultraplot-figures)
中提出的建议与反馈，我们对其进行了全面重写和测试，进一步完善了工作流。感谢维护者
提供的专业指导与支持。

感谢 [LINUX DO](https://linux.do/) 社区与平台提供的技术交流、反馈与支持。

## 相关链接

- [UltraPlot 官方文档](https://ultraplot.readthedocs.io/en/stable/)
- [UltraPlot 源代码](https://github.com/ultraplot/ultraplot)
- [本 skill 的许可证](LICENSE)
