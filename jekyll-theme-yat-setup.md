# Jekyll Theme Yat 配置指南

本文档说明如何使用 jekyll-theme-yat 主题。

## 已完成的配置

### 1. 创建了 Gemfile
定义了必要的 Jekyll 插件和主题依赖：
- jekyll-theme-yat: 主题
- jekyll-remote-theme: 远程主题支持
- jekyll-seo-tag: SEO 优化
- jekyll-sitemap: 网站地图
- jekyll-feed: RSS 订阅
- jekyll-spaceship: 扩展 Markdown 功能

### 2. 更新了 _config.yml
配置文件已更新为使用 jekyll-theme-yat 主题，主要配置包括：
- 远程主题配置
- 基本站点设置
- 语言和时区设置
- 作者信息
- Markdown 和 Sass 配置

## 使用方法

### GitHub Pages 部署（推荐）

如果要在 GitHub Pages 上部署博客，只需将更改推送到 GitHub 即可：

```bash
cd blog
git add Gemfile _config.yml
git commit -m "切换到 jekyll-theme-yat 主题"
git push
```

GitHub Pages 会自动构建和部署你的网站。

### 本地开发环境设置

如果你想在本地开发和预览博客，需要先安装 Ruby 和 Bundler：

```bash
# 安装 Ruby 和 Bundler（Ubuntu/Debian）
sudo apt update
sudo apt install ruby-full ruby-bundler

# 进入 blog 目录
cd blog

# 安装依赖
bundle install

# 启动本地服务器
bundle exec jekyll serve

# 访问 http://localhost:4000
```

## 主题自定义

### 修改 _config.yml 中的配置项：

```yaml
# 站点基本信息
title: Anderson's Blog
name: Anderson
description: Web Developer from Somewhere

# URL 配置（根据实际情况修改）
url: https://your-domain.com
baseurl: /blog  # 如果是子目录，设置为目录名
repository: yourusername/your-repo

# 作者信息
author:
  name: Anderson
  email: your-email@example.com
  github: Andersonhere

# 头像图片
avatar: https://your-avatar-url.com/image.png
```

### 创建新文章

在 `_posts/` 目录下创建新的 Markdown 文件，文件名格式为 `YYYY-MM-DD-title.md`：

```markdown
---
layout: post
title: 文章标题
date: 2026-04-17 13:30:00 +0800
categories: [分类1, 分类2]
tags: [标签1, 标签2]
---

文章内容...
```

### 主题特性

jekyll-theme-yat 主题提供以下特性：
- 夜间模式支持
- 响应式设计
- 代码高亮
- 图片画廊
- 数学公式（MathJAX）
- 流程图支持
- 搜索引擎优化
- 网站地图
- RSS 订阅

## 注意事项

1. **GitHub Pages 限制**：GitHub Pages 在安全模式下运行，可能限制某些插件功能。如果遇到问题，可以考虑使用 GitHub Actions 部署。

2. **中文内容**：已在 _config.yml 中设置 `lang: zh_CN`，确保中文内容正确显示。

3. **时区设置**：已设置为 `timezone: Asia/Shanghai`，确保文章日期正确显示。

## 后续步骤

1. 根据需要修改 _config.yml 中的配置项
2. 在 _posts/ 目录中创建博客文章
3. 可以创建自定义页面（如 pages/about.md）
4. 将更改推送到 GitHub，访问你的博客网址

## 参考链接

- [Jekyll Theme Yat 官方文档](https://github.com/jeffreytse/jekyll-theme-yat)
- [主题演示站](https://jeffreytse.github.io/jekyll-theme-yat)
- [Jekyll 官方文档](https://jekyllrb.com/docs/)
