# 小咪的生活档案

这里记录一只叫“小咪”的母幼猫怎样长大：她吃了什么、体重怎么变化、什么时候最有精神、遇到什么会紧张，以及照护者如何一点点理解她。

仓库既是小咪的长期档案，也是一个公开、脱敏、可追溯的养猫记录示例。记录不追求把每一天写得像病例，而是希望以后回头看时，仍能看见她具体的习惯和变化。

## 从这里开始

- [打开小咪的本地看板](dashboard.html)：最直观地查看体重曲线、进食节律、近期记录与待跟进事项。
- [读当前基线](01_profile/baseline.md)：了解她平时正常是什么样。
- [看最新日志](02_daily/logs/2026-07.md)：了解最近发生的事情。
- [打开完整索引](INDEX.md)：按健康、饮食、行为、环境等场景查找文件。

`dashboard.html` 不需要联网，下载仓库后可直接双击打开。它是现有记录的派生视图，不替代原始档案；数据更新后用 `python3 scripts/build_dashboard.py` 重建。

## 记录如何流动

```text
带日期的观察/测量
        ↓
月度日志或专题记录（事实源）
        ↓
基础档案与当前基线（当前摘要）
        ↓
跨维度分析与 dashboard.html（派生展示）
```

- 原始记录回答“发生了什么”。
- 当前摘要回答“小咪平时是什么样”。
- 派生分析回答“这些记录放在一起能看到什么趋势”。
- 历史导入、旧 AI 回答和日期报告只用于追溯，不自动代表当前状态。

详细维护规则见 [PROJECT_RULES.md](PROJECT_RULES.md)，智能体回答边界见 [AGENTS.md](AGENTS.md)。
尚未实施的结构化数据和自动检查计划见 [ROADMAP.md](ROADMAP.md)。

## 目录

- [`00_inbox/`](00_inbox/)：暂时还没分类的新信息。
- [`01_profile/`](01_profile/)：身份、偏好、成长时间线和当前基线。
- [`02_daily/`](02_daily/)：月度日志、作息和生活变化。
- [`03_health/`](03_health/)：体重、疫苗、驱虫、症状、用药和应急。
- [`04_nutrition/`](04_nutrition/)：主食、零食、饮水、摄入数据和反应。
- [`05_behavior_training/`](05_behavior_training/)：行为观察、压力源和训练。
- [`06_environment_supplies/`](06_environment_supplies/)：环境、清洁、安全、用品与丰容。
- [`07_knowledge/`](07_knowledge/)：与小咪个人事实分开的通用知识。
- [`08_questions_decisions/`](08_questions_decisions/)：问题、行动、实验和决策。
- [`09_media/`](09_media/)：已脱敏媒体、资料和生成图表。
- [`10_templates/`](10_templates/)：常用记录模板。
- [`11_insights/`](11_insights/)：跨维度派生数据和分析报告。

## 日常维护

1. 新事情先写日期、场景和观察，不急着解释原因。
2. 只有真正改变日常基线的信息，才同步到 `01_profile/baseline.md`。
3. 计划和待确认事项统一放入 `08_questions_decisions/action_queue.md`。
4. 更新派生数据后运行：

   ```bash
   python3 scripts/build_dashboard.py
   python3 scripts/check_repository.py
   ```

5. 提交前检查隐私与变更；远端 `git push` 必须由主人明确确认。

## 公开边界

仓库默认公开，不记录照护者姓名、联系方式、住址、医院会员信息、订单号或未打码票据。照片和视频也需要检查定位线索及 EXIF。完整要求见 [PRIVACY.md](PRIVACY.md)。

健康、用药、疫苗、驱虫、异常症状和急救相关内容只作为观察与沟通材料，不能替代兽医面诊。

## 许可

当前仓库公开可读，但暂未添加 LICENSE。公开可见不等于已经授权复用其中的小咪档案、文字、模板或代码。
