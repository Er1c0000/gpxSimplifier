# GPX 数据处理工具集

本项目是一个用于处理 GPX 格式文件的工具集，包含了 GPX 文件简化、合并、CSV 与 GPX 格式转换等功能。这些工具可以帮助你更方便地处理和分析 GPX 轨迹数据。

## 功能概述
1. **GPX 文件简化**：通过 `1_gpx_simplifier.py` 脚本，去除 GPX 文件中的冗余轨迹点，识别停留区域和移动段，减少数据量。
2. **GPX 文件合并**：使用 `2_gpx_merger.py` 脚本，将指定目录下的所有 GPX 文件合并为一个新的 GPX 文件，并统计合并后的轨迹点数。
3. **CSV 转 GPX**：`csv2gpx.py` 脚本可将 CSV 文件转换为 GPX 格式，支持时间戳、经纬度、海拔、速度和精度等信息的转换。
4. **GPX 转 CSV**：`3_gpx2csv.py` 脚本能够将指定目录下的所有 GPX 文件转换为 CSV 格式，方便后续数据分析。

## 安装依赖
本项目使用了 Python 的标准库和 `gpxpy` 库，你可以使用以下命令安装 `gpxpy`：
```bash
pip install gpxpy
```

## 使用方法

### 1. GPX 文件简化
```bash
python gpxSimplify/1_gpx_simplifier.py
```
- **参数说明**：在 `GPXSimplifier` 类的 `__init__` 方法中，可以调整停留半径、最小停留时间、每个停留区域保留的最大点数和判定移动的最小距离等参数。

### 2. GPX 文件合并
```bash
python gpxSimplify/2_gpx_merger.py
```
- **参数说明**：在脚本中，可以修改 `gpx_input_directory` 变量，指定包含 GPX 文件的输入目录。

### 3. CSV 转 GPX
```bash
python gpxSimplify/csv2gpx.py
```
- **参数说明**：在 `main` 函数中，可以修改 `input_file` 和 `output_file` 变量，指定输入的 CSV 文件和输出的 GPX 文件路径。

### 4. GPX 转 CSV
```bash
python gpxSimplify/3_gpx2csv.py
```
- **参数说明**：在脚本中，可以修改 `root_directory` 变量，指定要处理的根目录。

## 注意事项
- 请确保输入的 CSV 文件包含 `dataTime`、`longitude` 和 `latitude` 列，否则可能会导致转换失败。
- 在处理 GPX 文件时，如果文件格式不符合标准，可能会出现解析错误，请检查文件内容。

## 贡献
如果你发现任何问题或有改进建议，欢迎提交 Issues 或 Pull Requests。

## 许可证
本项目采用 [MIT 许可证](LICENSE)。