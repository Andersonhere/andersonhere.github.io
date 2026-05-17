---
title: LangGraph 核心概念笔记 — 从手写 Agent 到 Time Travel
date: 2026-05-17 23:30:00 +0800
categories: [AI Agent, LangGraph]
tags: [LangGraph, Agent, StateGraph, Checkpointer, ReAct, Python, 学习笔记]
---

> 一周时间从"手写 80 行 Agent"过渡到"LangGraph 玩 Time Travel"，把脑子里的概念图沉淀下来。
> 这篇是知识点速查版 —— 不讲怎么选框架（[那篇在这里](/posts/写完同一个Agent两遍后我才懂LangGraph在卷什么/)），只讲 LangGraph 的核心概念怎么咬合。

---

## 0. 学习路径回顾

```
手写极简版 SimpleAgent  →  手写极简版 ReActAgent  →  对比官方框架
        ↓
LangGraph 入门 (StateGraph / Node / Edge / State)
        ↓
LangGraph 进阶 (Checkpointer 持久化 + Time Travel 分叉)
        ↓
双框架同问题对比 → 输出博客
```

**结论**：没自己手写过一个 ReAct，直接学 LangGraph 会被 `Annotated[list, operator.add]` 这种东西劝退。**先理解循环，再理解抽象**。

---

## 1. ReAct 范式的本质

`ReAct = SimpleAgent + 循环 + 工具调用`

5 个不能省的要点：

1. **三段式 prompt**：`Thought → Action → Observation`
2. **正则解析**：从 LLM 输出里抠出 `Action: tool(args)` 或 `Finish[...]`
3. **Observation 用 user role 塞回 messages**：让 LLM 看到"上一步工具结果"
4. **终止条件**：`Finish[...]` 或 `max_iterations`
5. **`stop=["Observation:"]`**：防 LLM 自己编 Observation —— 这一点不写就栽

手写一遍后再看任何 Agent 框架，本质上都是这个循环 + 各种花式封装。

---

## 2. LangGraph 三大抽象

| 抽象 | 是什么 | 关键特性 |
|---|---|---|
| **StateGraph** | 有状态计算 DAG | 节点函数都是 `state → dict` |
| **State** | TypedDict + Annotated reducer | reducer 决定字段更新语义（覆盖 vs 追加） |
| **Edge** | 节点间路由 | 普通边 + 条件边（`add_conditional_edges`） |

**核心 mental model**：
> 节点是纯函数，控制流由数据结构（state + reducer）驱动。

这是声明式（declarative）相对命令式（imperative）的范式革命 —— 跟 React 的 `useState`、Redux 的 single source of truth 是同一种哲学。

---

## 3. Reducer 是什么 / 为什么重要

定义 state 时这样写：

```python
from typing import TypedDict, Annotated
import operator

class ReActState(TypedDict):
    messages: Annotated[list, operator.add]   # ← reducer
    iteration: int                              # 默认覆盖
    final_answer: str                           # 默认覆盖
```

- `Annotated[list, operator.add]` = "节点返回的新 messages 会被**追加**到老的后面"
- 没 Annotated 的字段（如 `iteration`） = "新值**覆盖**老值"

所以节点函数只需返回**增量**：

```python
def call_tool_node(state):
    obs = run_tool(...)
    return {
        "messages": [{"role": "user", "content": f"Observation: {obs}"}],  # 只返回新增的 1 条
        "iteration": state["iteration"] + 1,                                # 这个会覆盖
    }
```

**踩坑警告**：reducer 永远是追加。同一个 thread_id 第二次跑 `invoke({"messages":[system,user]})` 会让 messages 多出一份重复的 system + user。

**正确姿势**：**一个 thread_id = 一次对话生命周期**。新对话用新 ID，延续对话只传增量 user message。

---

## 4. Checkpointer 持久化 — `state + thread_id + checkpointer` 三位一体

| 组件 | 角色 |
|---|---|
| **state** | 内容（这次的对话/任务数据） |
| **thread_id** | 边界（这次对话归属哪个用户/会话） |
| **checkpointer** | 存储引擎（内存 / SQLite / Postgres / Redis） |

启用持久化的代价：**3 行**

```python
from langgraph.checkpoint.sqlite import SqliteSaver
with SqliteSaver.from_conn_string("agent.db") as cp:
    app = graph.compile(checkpointer=cp)
    app.invoke(state, config={"configurable": {"thread_id": "user-001"}})
```

**业务代码 0 行改动**，节点函数签名都不变。

### 为什么"接口同形 / 实现异化"很重要

`MemorySaver` / `SqliteSaver` / `PostgresSaver` 都实现同一个 `BaseCheckpointSaver` 抽象 —— 这是 **策略模式 + 依赖倒置 + 依赖注入** 三件套的实战体现。

**好处**：原型期用 Memory，开发期用 SQLite，生产期切 Postgres，一行代码改动。

---

## 5. Time Travel — 把 Git 模型搬到 Agent 状态上

| Git | LangGraph |
|---|---|
| commit | checkpoint |
| SHA | checkpoint_id |
| branch | thread_id |
| HEAD | thread 当前最新 cp |
| `git log` | `get_state_history(config)` |
| `git checkout <sha>` | `invoke(None, {"configurable": {"checkpoint_id": ...}})` |
| `git checkout -b new` | 从老 cp 用新 thread_id 重跑 |
| `git stash` + `git stash pop` | `interrupt` + `resume` |

**核心创新**：每个节点跑完**自动 commit**（Git 要手动）。

### 这个能力的 5 个生产级用途

1. **错误回放复现**：异常时定位到出错前 cp，一键重跑该步（无需重跑前 N-1 步）
2. **步进调试**（Agent 版 GDB）：`interrupt_after=["llm","tool"]` 让每节点自动停
3. **A/B Prompt 实验**：从同一 cp 用不同 thread_id 跑出多个分支并排对比
4. **HITL 人工介入**：高风险动作前 interrupt，审批人改 state 后 resume
5. **教学回放**：把精彩解题过程做成"录像"

每一个，自己写都是几百行 + 一个 bug 季。

---

## 6. State 字段拼写错误 — 框架不报错

**坑**：

```python
class State(TypedDict):
    messages: list
    iteration: int

def my_node(state):
    return {"messsages": [...]}   # 拼错了！
```

LangGraph 的 TypedDict 是运行时 dict，写错字段名只是多一个不被消费的 key。**节点拿不到默默走默认值，节点该崩才崩**。

**应对**：写完节点立刻 `print(state)` 验证字段存在。**加 checkpointer 后这种 bug 会被持久化进 DB 更难发现**。

---

## 7. 三个高密度记忆点

如果只能记三句话：

1. **节点是纯函数（state → dict 增量）**，控制流由 reducer 决定
2. **state + thread_id + checkpointer 三位一体** 让 Agent 跨进程恢复
3. **Time Travel = 每节点自动 commit 的 Git on Agent state**，免费送调试 / A-B / HITL 全套能力

---

## 8. 给同样在学的朋友的建议

- **先手写一个 ReAct**（80 行内），别上来就学 LangGraph
- **理解 reducer 那一刻 = 真正进入声明式范式**，建议用 print(state) 反复验证
- **第一次启用 checkpointer 时务必踩一次"reducer 重复追加"坑**（同 thread_id 重复 invoke），踩过就永生难忘
- **Time Travel 不是炫技**，是生产 Agent 必备能力（错误回放 / HITL / 灾备）

---

*详细代码 / 笔记 / 踩坑过程都在 [hello-agents 学习仓库](https://github.com/Andersonhere/hello-agents) 的 `learning-plan/week2/` 目录下。
更深入的"为什么选 LangGraph 而不是手写"在 [这篇博客](/posts/写完同一个Agent两遍后我才懂LangGraph在卷什么/)。*
