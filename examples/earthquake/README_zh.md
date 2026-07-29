[English](README.md) | **简体中文**

# UltraPlot Skill A/B 测试：2025 年全球 M5+ 地震

本示例针对同一个全球地震制图任务，对比两次相互独立生成的 UltraPlot 结果。
两组提示词的唯一区别是是否显式调用 `$ultraplot-figures`。

## 输入数据

- GeoJSON：[usgs_earthquakes_2025_m5plus.geojson](data/usgs_earthquakes_2025_m5plus.geojson)
- 来源查询：USGS FDSN event API，2025-01-01 至 2026-01-01，最小震级 5
- 要素：2,129 个已复核的三维点事件
- 事件时间范围：2025-01-01 04:39:18 UTC 至 2025-12-31 14:26:57 UTC
- 震级范围：5.0–8.8
- 震源深度范围：0–648.298 km
- 经度范围：−179.9105°–179.9604°
- 纬度范围：−65.1723°–87.0815°
- 经度、纬度、深度或震级缺失值：0

## 提示词控制

共同任务为：

> 绘图数据文件：`data/usgs_earthquakes_2025_m5plus.geojson`
>
> 图中能够展示 2025 年全球 M5 以上地震的空间分布、震级和深度特征，让读者
> 直观了解这些地震在全球的分布情况及其主要特征。
>
> 请提供可直接运行的 Python 代码，导出 PDF 和 PNG。

只有绘图指令发生变化：

| 条件 | 指令 |
|---|---|
| 使用 skill | `请使用 [$ultraplot-figures](../../SKILL.md) 绘图。` |
| 不使用 skill | `请使用 UltraPlot 绘图。` |

## 图件对比

| 使用 `$ultraplot-figures` | 不使用 skill |
|:---:|:---:|
| ![使用 skill 生成的全球地震图](with_skill/global_earthquakes_2025_m5plus_with_skill.png) | ![不使用 skill 生成的全球地震图](without_skill/global_earthquakes_2025_m5plus.png) |

## 输出文件

| 类型 | 使用 `$ultraplot-figures` | 不使用 skill |
|---|---|---|
| 绘图脚本 | [plot_global_earthquakes_with_skill.py](with_skill/plot_global_earthquakes_with_skill.py) | [plot_global_earthquakes_2025.py](without_skill/plot_global_earthquakes_2025.py) |
| PDF | [global_earthquakes_2025_m5plus_with_skill.pdf](with_skill/global_earthquakes_2025_m5plus_with_skill.pdf) | [global_earthquakes_2025_m5plus.pdf](without_skill/global_earthquakes_2025_m5plus.pdf) |
| PNG | [global_earthquakes_2025_m5plus_with_skill.png](with_skill/global_earthquakes_2025_m5plus_with_skill.png) | [global_earthquakes_2025_m5plus.png](without_skill/global_earthquakes_2025_m5plus.png) |
| 验收记录 | [verification_with_skill.json](with_skill/verification_with_skill.json) | 脚本内验证与终端报告 |

## 客观输出信息

| 项目 | 使用 `$ultraplot-figures` | 不使用 skill |
|---|---:|---:|
| PDF 页数 | 1 | 1 |
| PDF 页面尺寸 | 183.000 × 94.051 mm | 228.600 × 152.400 mm |
| PNG 像素尺寸 | 7,204 × 3,702 px | 2,700 × 1,800 px |
| PNG 分辨率元数据 | 999.998 dpi | 299.999 dpi |
