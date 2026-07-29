[English](README.md) | **简体中文**

# UltraPlot Figures

> 使用 UltraPlot 制作可复现、符合出版尺寸要求的静态科研图件。

`ultraplot-figures` 用于制作和修改静态科研图件，也可协助排查绘图问题、审阅图件并
核验输出。使用时，请提供绘图数据，并说明图件所对应的科学问题和作图目的；如有
版面尺寸、输出格式或期刊要求，也请一并说明。输出包括可复现、便于继续修改的
Python 绘图脚本及相应的渲染结果。

本仓库是一个 **Codex skill**，不是
[UltraPlot](https://github.com/ultraplot/ultraplot) Python 包，也不是独立绘图软件。

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

没有指定期刊或字体时，本 skill 保留 UltraPlot 当前生效的字体配置。缺少必要字形时，
仅扩展现有字体回退链，不替换其中的主要字体选择。

### 请求示例

```text
请使用 $ultraplot-figures 根据 results.csv 制图，比较各处理组与对照组的时间变化
和不确定性。图件用于展示各组的变化趋势及差异。请返回绘图脚本、PDF、PNG 和核验
说明。
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

有数据或绘图源文件时，Codex 会根据任务需要提供：

- 可独立运行、便于继续修改的 Python 绘图脚本；
- 需要实质性数据处理时使用的预处理脚本和处理后数据；
- 按要求尺寸生成的 PDF 和 PNG；
- 记录主要假设、数据处理、输出尺寸和未解决问题的核验说明。

只有 PDF 或栅格图片时，本 skill 只能检查可见内容和文件信息，不能从成图还原未提供
的数据、处理流程、统计方法或可复现代码。

本 skill 默认制作 Python 静态图件，不用于交互式 dashboard 或网页应用。部分
UltraPlot 功能需要额外依赖。用户明确提出的要求和目标期刊的现行规范优先于默认值。

## 示例

- [2025 年全球 M5+ 地震 skill 对照案例](examples/earthquake/README_zh.md)：
  在相同数据和提示词下，分别使用和不使用 `$ultraplot-figures` 生成图件。案例包含
  输入数据、可编辑脚本、PDF、PNG、预览图及文件信息。
- [预测值与真实值模型对照案例](examples/correlation-scatter-plot/README_zh.md)：
  使用相同 Excel 数据和提示词，对比 LR、SVR、GBRT 和 DNN 在四种地类下的图件。
  案例包含输入数据、可编辑脚本、PDF、PNG、预览图及核验信息。

这些案例用于说明工作方式，不作为效果基准测试。

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
中提出的建议与反馈，我们对 1.0 版本进行了全面重写和测试。感谢维护者提供的专业
指导与支持。

感谢 [LINUX DO](https://linux.do/) 社区与平台提供的技术交流、反馈与支持。

## 相关链接

- [UltraPlot 官方文档](https://ultraplot.readthedocs.io/en/stable/)
- [UltraPlot 源代码](https://github.com/ultraplot/ultraplot)
- [本 skill 的许可证](LICENSE)
