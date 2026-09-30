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

对于没有宽度要求的新出版图件，可以使用 UltraPlot 的 `nat2` 预设（总宽度 183 mm）。
未指定格式时，通常输出面向出版的 PDF 和 PNG；如果用户、期刊或现有项目已经规定尺寸
和格式，应以这些规定为准。

默认保留 UltraPlot 当前生效的字体配置。没有字体要求时，应选择与项目或期刊匹配、且
本地已安装并可复现的字体，不强行设置新的全局字体。许多期刊偏好清晰的无衬线风格，
例如，[Nature 要求图中文字使用无衬线字体，并优先推荐 Helvetica 或 Arial](https://www.nature.com/nature/for-authors/final-submission)。

对于中文文本，请选择符合用户、期刊或项目要求的本地 CJK 回退字体。已安装时可以使用
`Microsoft YaHei`（微软雅黑）作为示例；本 skill 不会下载或全局安装字体。栅格图使用
用户或项目规定的 DPI；仅输出矢量图时不要强行设置 DPI。

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

请将 UltraPlot 安装到实际运行绘图脚本的解释器中。MCP 服务也必须使用同一解释器，
不要把裸 `pip` 安装到无关环境：

```bash
<python> -m pip install "ultraplot[mcp]==2.7.0"
```

只有在项目明确要求时才改用其他精确的稳定版 2.7.x；不要使用不带版本约束的安装，
以免选到尚未支持的未来版本。

也可以使用 conda：

```bash
conda install -n <environment> -c conda-forge ultraplot
```

将 `<python>` 和 `<environment>` 替换为当前主机及项目规则选定的解释器/环境。在
Windows PowerShell 中，通常写成 `& 'D:\path\to\python.exe' -m pip ...`；在 POSIX
shell 中使用 `/path/to/python -m pip ...`。

需要地理投影时应另行安装 Cartopy；其他数据读取和处理库按具体任务安装。详细要求
见 UltraPlot [安装指南](https://ultraplot.readthedocs.io/en/stable/install.html)。

安装或更新本 skill 不会立即执行包安装。安装或更新后的首次调用会先在选定的绘图环境中
进行只读预检；满足安全条件时，随后可执行幂等的 MCP 引导。之后的普通图件任务也会执行
同一套预检，不依赖持久化的“首次使用”标记。仅审阅、状态查询和排障任务默认全程保持只读；
除非明确请求修复，不会自动安装或写入配置。

## 交付物与使用限制

有数据或绘图源文件时，Codex 只会根据任务需要保留：

- 简洁、可独立运行、便于继续修改的绘图代码；
- 需要实质性数据处理时使用的预处理代码，以及绘图实际使用的最终处理结果；
- 用户要求的最终图件；出版导向的静态图未指定格式时，通常保留 PDF 和 PNG。

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
