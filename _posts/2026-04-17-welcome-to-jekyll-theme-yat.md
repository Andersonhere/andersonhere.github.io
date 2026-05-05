---
layout: post
title: 欢迎使用 Jekyll Theme Yat 主题
date: 2026-04-17 01:00:00 +0800
categories: [博客, 技术]
tags: [Jekyll, GitHub Pages, 博客]
excerpt_image: /images/covers/2026-04-17-welcome-to-jekyll-theme-yat.jpg
---

你好！欢迎来到 Anderson 的博客。

本博客已成功切换到 [Jekyll Theme Yat](https://github.com/jeffreytse/jekyll-theme-yat) 主题。

## 关于这个主题

Jekyll Theme Yat 是一个简洁、现代且优雅的 Jekyll 博客主题，专为注重内容的作家设计。它具有以下特点：

- ✨ **夜间模式** - 支持深色模式，保护视力
- 📱 **响应式设计** - 在各种设备上都能完美显示
- 🎨 **代码高亮** - 使用 highlight.js 进行代码语法高亮
- 🖼️ **图片画廊** - 使用 PhotoSwipe 5 实现精美的图片预览
- 🔍 **SEO 优化** - 集成 Jekyll Seo Tag 插件
- 📝 **RSS 订阅** - 支持站点内容订阅
- 🌐 **MathJAX 支持** - 支持数学公式渲染
- 📊 **图表支持** - 支持 PlantUML 和 Mermaid 流程图

## 如何开始

### 修改配置

通过编辑 `_config.yml` 文件来个性化你的博客：

```yaml
# 站点基本信息
title: 你的博客标题
description: 你的博客描述

# 作者信息
author:
  name: 你的名字
  email: your.email@example.com
  github: your-github-username
```

### 创建新文章

在 `__posts/` 目录下创建新的 Markdown 文件，文件名格式为 `YYYY-MM-DD-title.md`。

文件头部需要包含以下 Front Matter：

```yaml
---
layout: post
title: 文章标题
date: 2026-04-17 14:00:00 +0800
categories: [分类1, 分类2]
tags: [标签1, 标签2]
---

**注意**：以上仅为示例格式，实际使用时请替换为真实的标签。
```

### Markdown 示例

以下是一些常用的 Markdown 语法示例：

#### 代码块

```python
def hello_world():
    print("Hello, Jekyll Theme Yat!")
```

#### 引用

> 简洁是复杂的最终形式。
> —— 莱昂纳多·达·芬奇

#### 无序列表

- 项目一
- 项目二
- 项目三

#### 表格

| 特性 | 支持状态 |
|------|---------|
| 夜间模式 | ✅ |
| 代码高亮 | ✅ |
| MathJAX | ✅ |
| 图片画廊 | ✅ |

## 获取帮助

如果需要更多帮助，可以参考：

- [Jekyll Theme Yat 官方文档](https://github.com/jeffreytse/jekyll-theme-yat)
- [主题演示站](https://jeffreytse.github.io/jekyll-theme-yat)
- [Jekyll 官方文档](https://jekyllrb.com/docs/)

祝你 blogging 愉快！
