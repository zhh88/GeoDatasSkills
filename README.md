# GeoDatasSkills

GeoDatasSkills 是一个“多源空间数据接入 Skill”的参考实现，用于将空间数据、多模态数据、时空数据转换成统一的浏览器端时空对象模型。

它的定位不是简单读取文件，而是一个多源异构数据转换引擎：

```text
格式识别
→ 字段识别
→ 空间几何解析
→ 时间维度统一
→ 多模态内容绑定
→ 语义标准化
→ 坐标转换
→ 数据质量校验
→ 统一时空对象模型
```

## 适用数据

- CSV / TSV 表格空间数据
- JSON 对象数组
- GeoJSON Feature / FeatureCollection
- WKT 点、线、面
- GPX-like 轨迹
- 轨迹数据
- 传感器时序数据
- 图片、视频、文本、文档等多模态元数据
- API 返回的空间对象

## 安装与运行

开发模式安装：

```bash
pip install -e ".[dev]"
```

CLI 示例：

```bash
geodataskills examples/sample_points.csv --out outputs/sample_dataset.json
geodataskills examples/sample_geojson.json --pretty
geodataskills examples/sample_points.csv --rules examples/sample_rules.json --output-mode compact --pretty
```

Python API：

```python
from geodataskills import GeoDataIngestionSkill

skill = GeoDataIngestionSkill()
dataset = skill.ingest("examples/sample_points.csv")

print(dataset.statistics.object_count)
print(dataset.bounds)
print(dataset.objects[0].geometry)
```

规则驱动接入：

```python
dataset = skill.ingest(
    "examples/sample_points.csv",
    rules={
        "fields": {
            "x": "lng",
            "y": "lat",
            "z": "height",
            "value": "risk",
            "type": "type",
            "time": "time",
            "image": "photo",
            "text": "description"
        },
        "defaults": {
            "z": 0,
            "type": "unknown"
        },
        "filters": [
            {"field": "risk", "op": "gte", "value": 70}
        ],
        "validation": {
            "required": ["x", "y"],
            "missing_policy": "invalid"
        },
        "output": {
            "mode": "standard",
            "drop_empty": True,
            "include_report": True
        }
    }
)

print(dataset.report)
```

## 统一模型

核心输出为 `UnifiedDataSet`：

```python
UnifiedDataSet(
    dataset_id="...",
    objects=[UnifiedSpatialObject(...)]
)
```

每个对象包含：

- `source`：数据来源
- `geometry`：点、线、面、体、轨迹、网格、点云等几何
- `time`：时间点、时间区间或时间序列
- `attributes`：业务属性
- `modality`：图片、视频、文本、传感器、文档等内容
- `semantic`：分类、标签、事件类型和关联关系
- `render`：后续三维建模和渲染提示
- `quality`：坐标、时间、字段完整性和可信度
- `report`：字段识别、过滤、缺省补充、无效数据等转换报告

## v0.2 规则能力

GeoDatasSkills v0.2 开始支持“输入-规则-输出”主链路：

- 字段覆盖：用户可以显式指定 `x/y/z/time/value/type/image/text` 对应字段。
- 缺省值：缺少高度、分类、数值等字段时可按规则补充。
- 筛选：支持 `eq/ne/gt/gte/lt/lte/in/not_in/exists/missing`。
- 必填校验：支持缺字段标记无效或直接丢弃。
- 输出模式：支持 `compact / standard / full / debug`。
- 转换报告：记录输入数量、输出数量、过滤数量、修复数量、字段决策和事件日志。
- Schema 画像：自动扫描字段类型、缺失数量、示例值、数值范围。
- 嵌套 JSON 展平：支持 `location.lng`、`metrics.risk` 等点路径字段。
- 坐标质量检查：检测经纬度越界、疑似经纬度反转、零坐标等问题。
- 多模态绑定：支持按对象 ID 或空间最近邻将图片、文本、视频、传感器记录绑定到空间对象。
- 输出摘要：自动生成对象数、过滤数、修复数、模态数量、质量警告数和字段映射摘要。
- 数据治理：支持单位转换、属性白名单/黑名单、polygon 自动闭合、重复点清理、轨迹按时间排序。

嵌套 JSON 示例：

```bash
geodataskills examples/sample_nested.json --pretty
geodataskills examples/sample_polygon.wkt --pretty
geodataskills examples/sample_track.gpx --pretty
```

数据治理规则示例：

```python
dataset = skill.ingest(
    rows,
    rules={
        "fields": {"x": "lng", "y": "lat", "z": "height_cm"},
        "unit_conversions": [
            {"field": "height_cm", "from_unit": "cm", "to_unit": "m"}
        ],
        "attribute_exclude": ["internal_note"],
        "geometry": {
            "close_polygons": True,
            "remove_duplicate_points": True,
            "sort_trajectory_by_time": True
        }
    }
)
```

多模态绑定示例：

```python
dataset = skill.ingest(
    "examples/sample_points.csv",
    rules={
        "modality_bindings": [
            {
                "source": "examples/sample_modalities.csv",
                "method": "id",
                "object_id_field": "id",
                "modality_id_field": "object_id",
                "modality_type_field": "modality",
                "uri_field": "uri",
                "content_field": "content",
                "time_field": "time"
            }
        ]
    }
)
```

## 模块结构

```text
src/geodataskills/
  models.py        # 统一数据模型
  detection.py     # 数据源格式识别
  fields.py        # 字段识别
  coordinates.py   # 坐标统一
  timeutils.py     # 时间统一
  parsers.py       # CSV / JSON / GeoJSON 解析
  normalize.py     # 标准化转换
  quality.py       # 数据质量校验
  skill.py         # Skill 主入口
  cli.py           # 命令行工具
```

## 技术价值

GeoDatasSkills 可以作为 Web 端空间大数据三维建模系统的第一层能力。它将异构数据转换为统一模型后，后续可以稳定接入：

- 空间索引构建
- 建模规则生成
- 交互意图解析
- 局部三维模型生成
- 动态 LOD 调度
- 资源回收与性能监测

## 运行测试

```bash
python -m unittest discover -s tests -p "test*_unittest.py" -v
```

如果安装了 `pytest`，也可以运行：

```bash
pytest
```
