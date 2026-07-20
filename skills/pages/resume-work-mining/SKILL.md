---
name: resume-work-mining
description: >-
  深度挖掘工作项技术内容并整理为简历/面试素材。逐个工作项结合用户陈述、策划/开发文档（xlsx/md）
  与 LetsGo Lua/C++ 代码库分析，产出结构化技术点、STAR 提炼句与待确认问题列表，
  写入 career/projects/{工作项}.md。
  Use when the user asks to 挖掘工作内容, 整理项目素材, 分析技术点, 深挖简历, 补充简历项目,
  or mentions a work item name and wants to produce resume/interview material.
---

# Resume Work Mining Skill

逐项深度挖掘工作内容，以"代码一手确认"为原则，产出可直接用于简历与面试的结构化素材。

---

## 仓库路径配置

| 资源 | 路径 |
|------|------|
| 简历初稿（项目经历基线） | `F:\PersonalWorkSpace\LiangLiangPrivateRepo\career\resume\简历初稿.md` |
| 简历正式版 | `F:\PersonalWorkSpace\LiangLiangPrivateRepo\career\resume\简历_景语亮.md` |
| 简历知识库 | `F:\PersonalWorkSpace\LiangLiangPrivateRepo\career\resume\简历知识库.md` |
| 项目资料目录 | `F:\PersonalWorkSpace\LiangLiangPrivateRepo\career\projects\` |
| 工作文件（xlsx/md） | `F:\PersonalWorkSpace\LiangLiangPrivateRepo\career\projects\work-files\` |
| 项目总览 | `F:\PersonalWorkSpace\LiangLiangPrivateRepo\career\projects\README.md` |

当前已有工作项文件：
- `career/projects/暑期快闪季.md`
- `career/projects/环绕物.md`
- `career/projects/痛包.md`

---

## 触发示例

- "帮我挖掘环绕物的工作内容"
- "深挖暑期快闪季技术点"
- "整理痛包项目的简历素材"
- "帮我补充 [项目名] 的技术分析"

---

## 工作流

### Step 1：读取上下文

1. 读取 `career/resume/简历初稿.md` ——了解已有项目经历描述的基线口径
2. 读取 `career/resume/简历_景语亮.md` ——了解简历正式版里该工作项的当前写法
3. 读取目标工作项文件（如 `career/projects/环绕物.md`）——掌握已有分析与待确认事项
4. 读取 `career/projects/work-files/` 下相关策划案/开发文档（xlsx 读 sheet 内容，md 全读）

### Step 2：代码库分析

**代码库根目录通常为** `E:\Dev2\UE\ProjectT\Content`（或用户指定路径）。

按工作项中已标注的代码路径进行定向分析：

```
-- 对每个技术点，执行以下操作（优先级由高到低）：
1. 直接读取代码文件（已知路径）→ 标注为 [一手]
2. 使用 Grep/Glob 搜索关键类名/函数名 → 定位后读取 → 标注为 [一手]
3. 无法定位时标注为 [待核实]，给出搜索建议
```

重点关注：
- 函数签名与关键逻辑（复杂逻辑的行号）
- 网络同步方式（RPC / Replication / Event）
- 状态机接入点
- 性能相关决策
- 错误处理与健壮性措施

### Step 3：产出结构

将分析结果写入 `career/projects/{工作项}.md`，格式如下：

```markdown
# {工作项名称} · {一句话定位}

> 状态：🟡 细化中 / ✅ 已确认。标注 `⚠️` 处需你确认参与度或补充资料。
> 代码依据说明：`[一手]` = 我已直接读代码确认；`[待核实]` = 由代码检索定位、尚未逐行核对。

## 概述
- 一句话定位
- 我的角色
- 业务背景
- 参考资料来源（指向 career/projects/work-files/ 下的文件）

## 我的职责与范围
- 主要/独立负责的模块
- 不含（明确非我负责的部分）

## 工作内容拆解
按功能模块列出，每项包含：
- 功能描述
- 我的实现
- 技术点（每点标注 [一手] 或 [待核实]）
- 代码位置

## 技术点（按技术维度汇总）
以下维度按实际情况选用：
- [网络 / 数据流]
- [3C-角色 / 状态机]
- [C++ / 性能表现]
- [工程 / 复用]
- [生命周期 / 健壮性]

每个技术点格式：
### [{维度}] {标题}
- 核心机制描述
- 关键代码路径（文件:函数:行号）
- 标注 [一手] 或 [待核实]

## 难点与解决方案
列出 3-5 个真实技术难点：
- **难点**：描述问题
- **方案**：描述解法及原因
- 标注 [一手] 或 [待核实]

## 量化结果 / 亮点
- 有数据支撑的指标（性能提升、复用次数等）
- ⚠️ 待补充的量化项

## 简历用提炼句（STAR 精简，候选）
3-5 条可直接写入简历的 bullet：
- 每条控制在 2-3 行内
- 动词开头，突出技术决策与结果
- 不确定的用 ⚠️ 标注

## ⚠️ 存疑 / 需补充
- [ ] 按优先级排列待确认事项
```

### Step 4：更新 README

更新 `career/projects/README.md` 中对应工作项的状态（⬜ → 🟡 → ✅）。

---

## 代码标注规范

| 标注 | 含义 |
|------|------|
| `[一手]` | 已直接读取该文件/函数，内容已确认 |
| `[待核实]` | 通过搜索定位到路径，但未逐行阅读核对 |
| `⚠️[待核实]` | 关键信息未确认，需用户或二次代码核对 |

---

## 注意事项

1. **优先一手确认**：能读代码的尽量读，不要猜测。读到即标 `[一手]`。
2. **明确职责边界**：若有多人协作，主动标注哪些是用户负责的，哪些是他人。
3. **存疑置后不编造**：不确定的内容放进"存疑"区，不要写入正文充数。
4. **简历口径优先**：产出内容以"能用于简历/面试"为最终目标，技术描述要有深度但不过度炫技。
5. **路径统一**：所有文件引用均指向 `career/projects/work-files/` 下的文件，不引用 `E:\找工\` 等外部路径。
