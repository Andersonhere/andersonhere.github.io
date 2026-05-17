---
title: 写完同一个 Agent 两遍后，我才懂 LangGraph 在卷什么
date: 2026-05-17 23:00:00 +0800
categories: [AI Agent, LangGraph]
tags: [Agent, LangGraph, ReAct, Python, LLM, 框架对比, 持久化]
---

> 用 80 行手写一个 ReAct Agent，再用 LangGraph 实现一遍。两版的最终答案完全一致。
> 那我为什么还要学这玩意儿？答案在第三个需求出现的时候。

---

## 一、起点：两版 Agent，同一个问题

为了对比公平，我用同一个问题、同一套工具、同一个 LLM，分别跑了两版 Agent：

- **左版**（HelloAgents 风格）：80 行手写 `MiniReActAgent`，类继承 + while 循环
- **右版**（LangGraph 风格）：用 `StateGraph` + 条件边声明式建图

问题：**"北京和上海今天哪个更热？热多少度？再算一下温差的 3 倍是多少？"**

需要 3 次工具调用：`get_weather` × 2 + `calculate` × 1。

跑出来的对比表：

| 维度 | HelloAgents 风格 | LangGraph 风格 |
|---|---|---|
| 代码行数（核心） | 83 行 | 73 行 |
| 耗时 | 46.45s | 48.99s |
| ReAct 迭代轮数 | 3 | 3 |
| 工具调用次数 | 3 | 3 |
| 最终 messages 数 | 9 | 9 |
| 最终答案 | 上海热 5°C，×3 = 15°C | 上海高 5°C，×3 = 15°C |

**第一感受：好像没什么区别？**

代码量打平，耗时打平（99% 是 LLM 调用，框架开销忽略不计），答案语义一致。

如果你只看这张表，结论会是"何必学 LangGraph，自己写就行"。

但这恰恰是大多数人对工程框架的最大误解。

---

## 二、转折：当我想拿 metrics 的时候

为了画上面这张表，我需要从两个 Agent 里抓出 `tool_calls / iterations / messages` 这些指标。

**LangGraph 版**：直接从 `result` 字典读：

```python
result = app.invoke(initial_state)
tool_calls = sum(1 for m in result["messages"] if m["content"].startswith("Observation:"))
iterations = result["iteration"]
total_messages = len(result["messages"])
```

**0 行框架代码改动**。

**HelloAgents 版**：`messages` 是 `run()` 内部的局部变量，外面拿不到。我只好回去改 Agent 源码：

```python
- messages = [...]
+ self.messages = [...]   # 暴露成属性
```

3 行改动。看似不多，但**这就是范式分水岭**。

---

## 三、范式之战：State 是一等公民，还是副作用

LangGraph 这种"state 天生可访问"的能力，不是 API 设计精巧，而是范式选择不同：

- **HelloAgents 风格 = 命令式**：state 是过程的**副作用**，藏在 `self.messages` 里。要观察 = 必须打破封装
- **LangGraph 风格 = 声明式**：state 是**一等公民**，节点是"读 state → 写 state"的纯函数。观察 = 天生免费

这跟 React 的 `useState`、Redux 的 single source of truth、函数式编程的 "data over behavior" 是**同一种哲学**：

> **用数据结构表达控制流，比用控制流操纵数据结构更可观测、可测试、可持久化。**

可观测性只是开胃菜。真正的盛宴在第四章。

---

## 四、真正的拐点：3 行 vs 25 行 + 5 个坑

现在加一个新需求：**"Agent 重启后能恢复上次对话"**。

**LangGraph 版** —— **3 行**：

```python
from langgraph.checkpoint.sqlite import SqliteSaver
with SqliteSaver.from_conn_string("agent.db") as cp:
    app = graph.compile(checkpointer=cp)
    app.invoke(state, config={"configurable": {"thread_id": "user-001"}})
```

业务代码 0 行改动，节点函数签名都不变。

**HelloAgents 版** —— **25 行 + 5 个坑**：

| 改动 | 行数 | 隐藏成本 |
|---|---|---|
| `__init__` 加 `thread_id` | +1 | — |
| `run()` 开头 load 历史 | +5 | 不存在文件怎么处理 |
| `run()` 结尾 save | +3 | 写一半进程被杀 = 文件半残 |
| 防止重复加 system | +3 | **就是我踩过的 reducer 坑** |
| thread_id 安全映射 | +3 | 路径注入漏洞 |
| 文件锁 | +5 | 不加 = race condition |

还有 5 个**没写在代码里**但躲不掉的工程问题：

- 文件 vs SQLite 怎么选？
- 序列化用 json 还是 pickle？
- messages 无限增长怎么压缩？
- 对话内容敏感，要不要加密？
- 错误恢复策略？

---

> **LangGraph 不是省了 22 行代码，它省了 22 行代码 + 5 个生产事故 + 一个团队季度。**

这才是工程框架的真正价值：**把分布式系统里"没人想第二次踩"的坑，做成默认行为**。

类比：用 SQLAlchemy vs 自己拼 SQL —— 不是为了少打字，是为了别在 SQL 注入上栽跟头。

---

## 五、不止持久化：5 个隐藏红利

checkpointer 一旦启用，下面这些能力**全部免费送**：

1. **错误回放复现**：异常时定位到出错前 checkpoint，一键重跑（无需重跑前 N-1 步、不烧 LLM token）
2. **步进调试**（Agent 版 GDB）：`interrupt_after=["llm","tool"]` 让每节点自动停，UI 提供 Step Over / Step Back
3. **A/B Prompt 实验**：从同一 checkpoint 用不同 thread_id 跑出多个分支并排对比，控制变量严格
4. **HITL 人工介入**：高风险动作前 interrupt，审批人改 state 后 resume —— 金融/医疗/客服的标配
5. **教学回放**：把精彩解题过程做成"录像"，时间轴拖动看 state 变化

每一个，自己写都是几百行 + 一个 bug 季。LangGraph 把它们抽象成同一套机制：**checkpointer + thread_id + checkpoint_id**。

---

## 六、什么时候不该用 LangGraph？

为了不让这篇变成无脑安利，给个反向清单：

- **纯 demo / 一次性脚本**：80 行手写更快，依赖更轻
- **团队还没准备好理解 reducer / state schema**：学习曲线陡峭，强行上会变成"半懂不懂的 LangGraph 代码"，比手写还难维护
- **对延迟极致敏感的场景**：每个节点跑完都自动 checkpoint 写 IO，能被绕开但需要额外配置

---

## 结语

回到开头那张对比表：

> 80 行手写 vs LangGraph，hello world 阶段确实打平。

但**选框架不看 hello world，看加第三个需求时谁还能优雅**。

- 第一个需求（让 Agent 跑通）—— 都简单。
- 第二个需求（拿 metrics）—— 命令式范式开始打破封装。
- 第三个需求（持久化）—— 25 行 + 5 个坑 vs 3 行。
- 第四个需求（A/B / HITL / time travel）—— 命令式版基本要重写整个架构。

工程框架的护城河，从来不在 hello world 里。

---

*这篇博客的全部代码 / 数据 / 笔记都在我的 [hello-agents 学习仓库](https://github.com/Andersonhere/hello-agents) 的 `learning-plan/week2/` 目录下，欢迎 fork 跟读。*
