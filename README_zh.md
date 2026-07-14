[English](README.md) | **简体中文**

# UltraPlot 科研图件 Skill

> 使用 UltraPlot 制作、修改和检查静态科研图。

[GitHub 仓库](https://github.com/lwq-star/ultraplot-figures)

`ultraplot-figures` 是一个 Codex skill。你只需要提供数据并说明想让图件表达什么，Codex 会编写可编辑的 Python 脚本、生成图件并检查输出文件。它也可以修改已有绘图脚本，或者检查 PDF、TIFF、SVG 和 PNG 文件。

> [!CAUTION]
> **不要把本 skill 生成或修改的图件未经作者复核就直接用于投稿。** 生成的代码、图件和检查结果都可能有误。本 skill 可以核对数据筛选、变量对应、版式和导出文件，但不能替作者判断数据、方法、统计结果和结论是否可靠。投稿前请检查数据和代码，确认正文、图件和图注一致，并再次对照目标期刊最新的官方要求。

## 在哪里使用

这个 skill 要在支持本地 skills 的 Codex Desktop 或 Codex CLI 对话中使用。它不是独立绘图软件，也不是可以在 Python 中 `import` 的包。

适合用它完成这些任务：

- 根据数据制作科研图；
- 不知道画什么时，让 Codex 推荐合适的图件；
- 修改已有脚本或图件；
- 按期刊或出版商要求准备文件；
- 检查导出图件的尺寸、分辨率、字体和其他文件设置。

## 为什么需要这个项目

本项目帮助 AI 编写可复现的科研绘图代码。整个流程包括理解数据和作图目的、生成可修改脚本、导出正式图件和复核结果。

通用 AI 可以很快写出绘图代码，但代码能运行，不代表图件可复现、科学表达清楚或适合投稿。本 skill 以 UltraPlot 为核心：

- 根据数据结构、科学问题和读者需要选择合适的图型，目标不明确时先给出几个可解释方案；
- 生成从输入数据到最终图件可重复运行的 Python 代码，必要时将复杂预处理与绘图分开；
- 处理多面板、期刊尺寸、无障碍配色、图例、地图、栅格、Taylor 图和组学图等常见科研绘图需求；
- 将绘图脚本、临时检查文件和正式交付物分开，并在作者复核前核对成图是否符合原始要求。

只要 AI 模型仍需要额外规则才能稳定生成可复现的科研图件，本项目就会继续维护，并跟进 UltraPlot 和期刊要求。当这些能力成为模型可靠的默认能力后，再逐步精简。

## 安装

### 让 Codex 从 GitHub 安装

让 Codex 从仓库根目录安装该 skill：

```text
请使用 $skill-installer 从 https://github.com/lwq-star/ultraplot-figures 安装 ultraplot-figures。该 skill 位于仓库根目录（路径 `.`），安装名称使用 `ultraplot-figures`。
```

安装后可在下一轮调用。如果 Codex 还没有识别新 skill，再新建一个任务并用名称调用。

### 手动安装

1. 下载或克隆 [GitHub 仓库](https://github.com/lwq-star/ultraplot-figures)。
2. 将它复制到 `$CODEX_HOME/skills/ultraplot-figures`。如果没有设置 `CODEX_HOME`，常见位置是：
   - Windows：`%USERPROFILE%\.codex\skills\ultraplot-figures`
   - macOS/Linux：`~/.codex/skills/ultraplot-figures`
3. 确认该目录下直接包含 `SKILL.md`、`VERSION`、`agents/`、`references/` 和 `scripts/`。README 文件和 `examples/` 属于项目文档。
4. 下一轮使用 `$ultraplot-figures` 调用。如果没有识别，再新建一个 Codex 任务。

复制 skill 文件夹不会自动安装 Python 绘图库。

## Release 更新检查

已安装版本记录在 `VERSION` 中。使用本 skill 时，每个本地日历日最多检查一次最新的
稳定版 [GitHub Release](https://github.com/lwq-star/ultraplot-figures/releases)。这是
调用 skill 时进行的检查，不是后台常驻服务。

- 检查过程不会下载、安装或替换任何 skill 文件。
- 发现新稳定版后，Codex 会说明当前版本和最新版本、建议更新、提供 Release
  链接，并给出一条可以直接发送给 Codex 的更新请求。
- 设置 `ULTRAPLOT_FIGURES_UPDATE_CHECK=0` 可关闭自动检查。

可直接发送给 Codex 的更新请求：

```text
请将我已安装的 ultraplot-figures skill 更新到最新稳定版本：https://github.com/lwq-star/ultraplot-figures/releases/latest
```

手动命令：

```bash
python scripts/update_skill.py --check
python scripts/update_skill.py --auto
python scripts/update_skill.py --self-test
```

## 使用前需要准备

使用前需要：

- 支持本地 skills 的 Codex Desktop 或 Codex CLI；
- Codex 可以运行的 Python 3.10 或更高版本环境；
- 该环境中已经安装 UltraPlot、Matplotlib 和 NumPy；
- Codex 可以读取的数据、脚本或图件路径。

这个 skill 已在 UltraPlot 2.4.x 上通过检查。表格数据通常还需要 pandas，文件检查需要 Pillow 和 `pypdf`，Excel 文件需要 `openpyxl`，Parquet 文件通常需要 `pyarrow`。地图、统计分析和组学图可能需要其他软件包，只安装当前任务用得到的依赖即可。如果准备投稿，最好同时提供目标期刊最新的图件要求。

## 快速开始

提问时写清楚 skill 名称、输入文件、希望读者看懂的内容和需要的输出：

```text
请使用 $ultraplot-figures。
数据：[文件或文件夹路径]
展示：[变量、比较、趋势或地图]
用途：[希望读者从图中看懂什么]
输出：[Python 脚本和 PDF/TIFF/SVG/PNG]
```

如果不知道应该画什么，可以直接说：“请先查看数据，推荐 1–3 种合适的图件，说明每种图能看出什么，并推荐一种。”

## 目录

- [在哪里使用](#在哪里使用)
- [为什么需要这个项目](#为什么需要这个项目)
- [安装](#安装)
- [Release 更新检查](#release-更新检查)
- [使用前需要准备](#使用前需要准备)
- [快速开始](#快速开始)
- [示例](#示例)
- [它会怎样处理任务](#它会怎样处理任务)
- [你会得到什么](#你会得到什么)
- [期刊要求和投稿前检查](#期刊要求和投稿前检查)
- [默认字体设置](#默认字体设置)
- [支持的图件类型](#支持的图件类型)
- [使用限制](#使用限制)
- [反馈与联系](#反馈与联系)
- [参考的软件和项目](#参考的软件和项目)
- [致谢](#致谢)
- [科研绘图参考文献](#科研绘图参考文献)

## 示例

- [2025 年全球 M5+ 地震 skill 对照案例](examples/earthquake-skill-comparison/README_zh.md)：
  在相同数据和相同提示词下，分别允许和不允许使用 `$ultraplot-figures`
  生成图件。案例包含输入数据、可编辑脚本、PDF 和 TIFF、预览图及文件信息。

## 它会怎样处理任务

1. Codex 先读取文件，确认你想展示什么、使用哪些记录，以及需要哪些输出文件。
2. 它把每项读者判断映射到合适的视觉证据。明确要求一张图时仍只画一张；若请求包含多个科学方面，则可能使用让每个方面都可读的最少面板。
3. 如果还没有明确图件，它会先查看数据，给出 1–3 种合适的方案。只有不同选择会改变图意时才会提问。
4. 大量清洗、合并、建模或重投影会与绘图脚本分开处理。
5. Codex 先生成草稿，检查内容和版式，再导出正式文件并检查文件本身。

期刊图、地图、统计图和多面板图会增加相应检查。skill 不会擅自增加面板，也不会加入数据和分析无法支持的科学结论。

## 你会得到什么

- 一个可以直接运行的 Python 绘图脚本；
- 必要时单独提供的预处理脚本和经过核对的中间数据；
- 用户要求的 PDF、TIFF、SVG 或 PNG 文件；
- 一份简短说明，列出重要筛选、记录数量、最终尺寸、检查结果和仍需作者确认的问题。

后续修改应以绘图脚本和输入数据为准，导出的图件只是输出文件。

## 期刊要求和投稿前检查

不同期刊的要求并不相同，因此 skill 会按以下方式处理：

- **指定了期刊或出版商：** 以其最新官方要求作为尺寸、格式、分辨率、字体、透明度和文件大小的目标。
- **部分设置缺失：** 保留所有明确设置，只为缺失项使用默认值。目标场合和宽度未知时，尺寸回退使用当前 `nat2` 的 183 mm 宽度，高度自动确定。格式未知时默认使用 PDF 加 TIFF；TIFF 的其他文件设置未指定时，使用 600 dpi、不透明 RGB 和无损 LZW。这些是 skill 回退，不是通用期刊规则。

交付图件前，skill 会检查：

1. 每项请求的读者判断是否都有合适证据，以及是否使用了正确的记录、筛选条件、面板、变量、单位和标注；
2. 文字、图例、色标和数据是否清楚，有没有重叠或被裁切；
3. 导出文件的格式、尺寸、分辨率、透明度和其他文件设置是否符合要求；PDF 和 SVG 可以检查字体资源，栅格图中的文字只能检查显示效果；
4. 按实际使用尺寸查看时，图件是否容易理解。

## 默认字体设置

没有指定期刊或字体时，默认使用 9 pt 无衬线 TeX Gyre Heros。它是开源的 Helvetica 风格字体，在小尺寸图件中较清楚，也便于跨系统复现。它符合许多期刊常见的无衬线风格。例如，[Nature 要求图中文字使用无衬线字体，并优先推荐 Helvetica 或 Arial](https://www.nature.com/nature/for-authors/final-submission)。

## 支持的图件类型

这个 skill 支持折线图、散点图、柱状图、区间图、分布图、热图、等值线图、地图、栅格和气候场、Taylor 图、模型诊断图、火山图、Manhattan 图、PCA/UMAP 以及其他静态多面板图。

## 使用限制

- 默认输出 Python 静态图件，不是交互式 dashboard 或网页应用。
- 只有导出图件时，无法完成依赖源数据、分析过程或绘图代码的检查。

## 反馈与联系

欢迎反馈 bug、使用体验和改进建议。如果遇到报错、说明不清、输出异常，或有任何不符合预期之处，请优先在 [GitHub Issues](https://github.com/lwq-star/ultraplot-figures/issues) 反馈。条件允许时，请附上 Python 与 UltraPlot 版本、相关提示词或脚本、最小可复现示例及完整报错信息。

如不便公开反馈，也可以发送邮件至 [laiwenqinstar@gmail.com](mailto:laiwenqinstar@gmail.com)。请勿在 Issue 或邮件中提供密码、API 密钥、机密数据或其他敏感信息。

## 参考的软件和项目

本 skill 使用或直接参考了以下 GitHub 项目：

- [UltraPlot](https://github.com/ultraplot/ultraplot)
- [Matplotlib](https://github.com/matplotlib/matplotlib)
- [NumPy](https://github.com/numpy/numpy)
- [pandas](https://github.com/pandas-dev/pandas)
- [Pillow](https://github.com/python-pillow/Pillow)
- [pypdf](https://github.com/py-pdf/pypdf)
- [Cartopy](https://github.com/SciTools/cartopy)

工作流程还对照了以下开源绘图 skills：

- [K-Dense scientific-agent-skills](https://github.com/k-dense-ai/scientific-agent-skills/tree/main/skills/scientific-visualization)
- [scipilot-figure-skill](https://github.com/Haojae/scipilot-figure-skill)
- [nature-skills](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-figure)
- [pythesis-plot](https://github.com/stephenlzc/pythesis-plot)
- [scientific-plotting-skill](https://github.com/dazhiyang/scientific-plotting-skill)

## 致谢

本 skill 围绕开源 [UltraPlot](https://github.com/ultraplot/ultraplot) 项目构建。诚挚感谢 UltraPlot 的维护者与贡献者开发并开放这一科研绘图库，为本工作流程提供了重要基础。

同时感谢 [LINUX DO](https://linux.do/) 社区与平台提供的技术交流、反馈与支持，帮助本项目不断完善。

## 科研绘图参考文献

图件规划、视觉编码、不确定性、可读性和配色规则还参考了以下论文：

- Cleveland, W. S., & McGill, R. (1984). Graphical perception: Theory, experimentation, and application to the development of graphical methods. *Journal of the American Statistical Association*. [DOI](https://doi.org/10.2307/2288400)
- Cleveland, W. S., & McGill, R. (1985). Graphical perception and graphical methods for analyzing scientific data. *Science*. [DOI](https://doi.org/10.1126/science.229.4716.828)
- Kelleher, C., & Wagener, T. (2011). Ten guidelines for effective data visualization in scientific publications. *Environmental Modelling & Software*. [DOI](https://doi.org/10.1016/j.envsoft.2010.12.006)
- Rougier, N. P., Droettboom, M., & Bourne, P. E. (2014). Ten simple rules for better figures. *PLOS Computational Biology*. [DOI](https://doi.org/10.1371/journal.pcbi.1003833)
- Weissgerber, T. L., Milic, N. M., Winham, S. J., & Garovic, V. D. (2015). Beyond bar and line graphs: Time for a new data presentation paradigm. *PLOS Biology*. [DOI](https://doi.org/10.1371/journal.pbio.1002128)
- Midway, S. R. (2020). Principles of effective data visualization. *Patterns*. [DOI](https://doi.org/10.1016/j.patter.2020.100141)
- Jambor, H. K., et al. (2021). Creating clear and informative image-based figures for scientific publications. *PLOS Biology*. [DOI](https://doi.org/10.1371/journal.pbio.3001161)
- Crameri, F., Shephard, G. E., & Heron, P. J. (2020). The misuse of colour in science communication. *Nature Communications*. [DOI](https://doi.org/10.1038/s41467-020-19160-7)
- Wong, B. (2011). Points of view: Color blindness. *Nature Methods*. [DOI](https://doi.org/10.1038/nmeth.1618)

配色参考：[Okabe 和 Ito，Color Universal Design](https://jfly.uni-koeln.de/color/)。
