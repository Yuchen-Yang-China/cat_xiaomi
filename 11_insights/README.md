# 跨维度洞察

这里把体重、饮食、排泄、作息、行为、健康和环境记录放在同一时间线上看。它的作用是发现线索，不是给小咪打“健康分”或替代兽医判断。

## 文件

- [`data/current_snapshot.json`](data/current_snapshot.json)：截至 2026-07-13 的机器可读派生快照。
- [`reports/2026-07-13_multidimensional_snapshot.md`](reports/2026-07-13_multidimensional_snapshot.md)：给主人阅读的综合分析。
- [`../dashboard.html`](../dashboard.html)：由快照生成的离线总览。
- [`../scripts/build_dashboard.py`](../scripts/build_dashboard.py)：看板构建与一致性检查脚本。

## 数据类型

| 类型 | 含义 | 示例 |
| --- | --- | --- |
| 记录值 | 有日期和数值的原始记录，但测量方式可能仍有缺口 | 2026-07-10 体重 1300 g |
| 观察值 | 主人直接看到或回顾的现象，没有精密测量 | 每天约 4-5 个尿团 |
| 估算值 | 由插值、折算或假设得到 | 观察期体重约 1.25 kg |
| 推断值 | 多条记录放在一起形成的解释 | 夜间活动与进食高峰方向一致 |
| 参考值 | 来自产品资料或外部知识，只作对照 | 按 4.2 kcal/g 粗估热量 |

## 使用边界

- `current_snapshot.json` 是派生数据，不是新的事实源。每个关键字段必须保留 `source` 和 `limitation`。
- 出现冲突时，回到带日期的月度日志和专题记录核对；较新的原始记录优先。
- 单次 24 小时观察标记为 `n=1`，不能外推成稳定规律。
- 水碗减少量不能写成精确饮水量；主人观察不能写成诊断。
- 环境“未知”只表示仓库没记录，不代表家里没有相应资源。
- 不生成健康总分、幸福指数或没有可靠依据的相关性。

## 更新流程

1. 先更新原始日志或专题文件。
2. 如当前基线发生变化，更新 `01_profile/baseline.md`。
3. 重新核算并更新 `data/current_snapshot.json` 的 `as_of`、来源和局限。
4. 运行：

   ```bash
   python3 scripts/build_dashboard.py
   python3 scripts/check_repository.py
   ```

5. 打开 `dashboard.html` 检查桌面和手机布局、链接及交互。

JSON 采用 UTF-8，并保留中文显示文案；键名使用 ASCII，便于脚本处理。
