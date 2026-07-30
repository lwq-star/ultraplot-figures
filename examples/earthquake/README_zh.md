[English](README.md) | **简体中文**

# UltraPlot Skill A/B 测试：2025 年全球 M5+ 地震

## 输入数据

- GeoJSON：[usgs_earthquakes_2025_m5plus.geojson](data/usgs_earthquakes_2025_m5plus.geojson)
- 原始要素数：2,129
- 保留地震数：2,128
- 明确排除：1 条 `properties.type == "landslide"` 的记录
- 震级范围：M5.0-M8.8；深度范围：3.0-648.298 km

## 提示词控制

| 条件 | 绘图指令 |
|---|---|
| 使用 skill | `请使用 [$ultraplot-figures](../../SKILL.md) 绘图。` |
| 不使用 skill | `请使用 UltraPlot 绘图。` |

两组均要求提供可直接运行的 Python 代码并导出 PDF 和 PNG。

## 图件对比

### 使用 `ultraplot-figures`

![skill 启用地震图](with_skill/earthquakes_2025_m5plus_global.png)

### 不使用 skill

![skill 禁用地震图](without_skill/earthquakes_2025_m5plus_global.png)

## 保留文件

| 类型 | 使用 skill | 不使用 skill |
|---|---|---|
| 数据处理 | [process_earthquakes.py](with_skill/process_earthquakes.py) | 位于绘图脚本中 |
| 绘图 | [plot_earthquakes.py](with_skill/plot_earthquakes.py) | [plot_earthquakes_2025_ultraplot.py](without_skill/plot_earthquakes_2025_ultraplot.py) |
| 处理后事件 | [earthquakes_2025_m5plus_processed.csv](with_skill/earthquakes_2025_m5plus_processed.csv) | 不单独写出 |
| 震级汇总 | [magnitude_exceedance.csv](with_skill/magnitude_exceedance.csv) | 在内存中计算 |
| 深度汇总 | [depth_classes.csv](with_skill/depth_classes.csv) | 在内存中计算 |
| 排除记录 | [excluded_features.csv](with_skill/excluded_features.csv) | 在内存中计数 |
| PDF | [earthquakes_2025_m5plus_global.pdf](with_skill/earthquakes_2025_m5plus_global.pdf) | [earthquakes_2025_m5plus_global.pdf](without_skill/earthquakes_2025_m5plus_global.pdf) |
| PNG | [earthquakes_2025_m5plus_global.png](with_skill/earthquakes_2025_m5plus_global.png) | [earthquakes_2025_m5plus_global.png](without_skill/earthquakes_2025_m5plus_global.png) |

## 客观输出信息

| 项目 | 使用 skill | 不使用 skill |
|---|---:|---:|
| PDF 页数 | 1 | 1 |
| PDF 页面尺寸 | 183.000 x 116.638 mm | 406.400 x 254.000 mm |
| PNG 像素尺寸 | 7,204 x 4,592 px | 4,800 x 3,000 px |
| PNG 分辨率元数据 | 999.998 dpi | 299.999 dpi |
| 显示投影 | Plate Carree，中央经线 0 | Robinson，中央经线 150 E |
