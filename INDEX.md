# 项目索引

这里是主人和智能体共同使用的导航页。先看当前状态，再按需要下钻；历史快照不参与当前判断。

## 30 秒了解小咪

- [本地总览看板](dashboard.html)：体重、摄入节律、近期观察和待跟进事项。
- [当前基线](01_profile/baseline.md)：小咪平时吃、喝、睡、排泄和互动是什么样。
- [基础档案](01_profile/cat_profile.md)：身份、当前主食、疫苗驱虫和健康摘要。
- [近期行动队列](08_questions_decisions/action_queue.md)：下一次需要观察、确认或安排的事情。
- [最新日常日志](02_daily/logs/2026-07.md)：最近发生了什么。
- [2026-07-13 多维分析快照](11_insights/reports/2026-07-13_multidimensional_snapshot.md)：截至该日期的数据能说明什么、还不能说明什么；当前数值以看板和原始记录为准。

## 按问题查找

### 小咪突然不舒服

1. 先看[应急预案](03_health/emergency_plan.md)。
2. 对照[当前基线](01_profile/baseline.md)和[症状记录](03_health/symptoms_observations.md)。
3. 核对[当前用药](03_health/medications.md)、[疫苗](03_health/vaccines.md)、[驱虫](03_health/deworming_flea_tick.md)和[就诊记录](03_health/vet_visits.md)。
4. 用[症状事件模板](10_templates/symptom_event_template.md)补齐时间、吃喝、排泄、精神和照片/视频。

### 想看体重、饮食或排泄趋势

- [体重与成长](03_health/weight_growth.md)
- [当前饮食方案](04_nutrition/diet_plan.md)
- [喂食记录](04_nutrition/feeding_log.md)
- [摄入连续观察](04_nutrition/intake_observations.md)
- [饮水记录](04_nutrition/water_hydration.md)
- [零食与反应](04_nutrition/treats_reactions.md)
- [24 小时摄入报告](04_nutrition/reports/2026-07-07_24h_intake_analysis.md)

### 想理解或调整行为

- [行为观察](05_behavior_training/behavior_observations.md)
- [当前训练计划](05_behavior_training/training_plan.md)
- [压力源](05_behavior_training/stress_triggers.md)
- [咬人和玩耍边界](05_behavior_training/biting_play.md)
- [社会化与适应](05_behavior_training/socialization.md)
- [行为事件模板](10_templates/behavior_event_template.md)

### 想检查环境与用品

- [居家环境](06_environment_supplies/home_setup.md)
- [清洁与安全](06_environment_supplies/cleaning_safety.md)
- [丰容与玩耍](06_environment_supplies/enrichment_play.md)
- [梳毛与护理](06_environment_supplies/grooming.md)
- [用品清单](06_environment_supplies/supplies_inventory.md)

### 想复盘一次选择

- [开放问题](08_questions_decisions/questions.md)
- [行动队列](08_questions_decisions/action_queue.md)
- [实验记录](08_questions_decisions/experiments.md)
- [决策记录](08_questions_decisions/decisions.md)
- [历史 AI 回答](08_questions_decisions/ai_answers.md)

## 数据与生成物

- [跨维度洞察说明](11_insights/README.md)
- [当前派生数据](11_insights/data/current_snapshot.json)
- [饮食数据目录](04_nutrition/data/)
- [图表与脱敏附件](09_media/README.md)
- [看板构建脚本](scripts/build_dashboard.py)
- [仓库优化路线图](ROADMAP.md)

数据类型统一为：记录值、观察值、估算值、推断值和参考值。`11_insights/` 与 `dashboard.html` 是展示层；出现冲突时，应回到带日期的原始记录核对。

## 历史入口

- [2026-07-06 导入确认快照](08_questions_decisions/confirmation_questions_2026-07-06.md)
- [成长时间线](01_profile/timeline.md)
- [知识库](07_knowledge/README.md)
- [全部模板](10_templates/README.md)
