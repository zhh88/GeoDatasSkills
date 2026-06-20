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
pytest
```
