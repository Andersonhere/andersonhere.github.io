---
name: wechat-article
description: 获取微信公众号文章内容并发布到博客。当用户提供公众号文章链接时，自动提取文章标题和正文，整理为博客文章格式。
license: MIT
compatibility: 适用于 Jekyll 博客
metadata:
  author: WorkGuide
  version: "1.0"
---

# 微信公众号文章获取 Skill

这是一个用于获取微信公众号文章内容并发布到 Jekyll 博客的工具。

---

## 触发条件

**必须使用此 skill 当：**
- 用户提供微信公众号文章链接（`mp.weixin.qq.com/s/...`）
- 用户说"帮我获取这篇公众号文章"
- 用户说"把这个公众号文章发到博客"

---

## 工作原理

### 为什么不能直接获取？

微信公众号文章（`mp.weixin.qq.com`）有反爬虫机制：
- 需要特定的 User-Agent
- 部分内容通过 JavaScript 动态加载
- WebFetch 工具可能会被拦截

### 解决方案

使用 `curl` 命令配合正确的 User-Agent 获取原始 HTML，然后用 Python 提取内容：

```bash
# 1. 获取原始 HTML
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "文章URL" > /tmp/wx_article.html

# 2. 提取标题
grep -oP 'og:title" content="[^"]*' /tmp/wx_article.html | sed 's/og:title" content="//'

# 3. 用 Python 提取正文
python3 提取脚本
```

---

## 执行步骤

### Step 1: 获取文章 HTML

```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "{文章URL}" > /tmp/wx_article.html
```

### Step 2: 提取文章标题

```bash
# 从 og:title meta 标签提取
grep -oP 'og:title" content="[^"]*' /tmp/wx_article.html | sed 's/og:title" content="//'
```

### Step 3: 提取正文内容

使用 Python 脚本提取并清理正文：

```python
import re
import html

with open('/tmp/wx_article.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 找到 js_content div
match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*</div>', content, re.DOTALL)
if match:
    article = match.group(1)
else:
    article = content

# 移除 HTML 标签，保留文本
text = re.sub(r'<script[^>]*>.*?</script>', '', article, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', text)
text = html.unescape(text)

# 清理多余空白
text = re.sub(r'\n\s*\n', '\n\n', text)
text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)

print(text)
```

### Step 4: 整理为博客文章格式

将提取的内容整理为 Jekyll 博客文章格式：

```markdown
---
title: {文章标题}
date: {当前日期时间}
categories: [{分类}]
tags: [{标签}]
excerpt_image: /images/covers/{封面图}
---

> 本文梳理自微信公众号文章，原作者：{公众号名称}

## 引言

{文章开头内容}

---

## 一、{第一个章节标题}

{章节内容}

---

## 总结

{总结内容}
```

### Step 5: 发布到博客

```bash
# 创建文章文件
cat > "_posts/{日期}-{标题}.md" << 'EOF'
文章内容
EOF

# 提交并推送
git add _posts/
git commit -m "发布：{文章标题}"
git push
```

---

## 完整提取脚本

将以下脚本保存为 `/tmp/extract_wechat.py`：

```python
#!/usr/bin/env python3
"""微信公众号文章提取脚本"""

import re
import html
import sys

def extract_wechat_article(html_file):
    """从 HTML 文件提取微信公众号文章内容"""
    
    with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取标题
    title_match = re.search(r'og:title" content="([^"]*)"', content)
    title = title_match.group(1) if title_match else "未知标题"
    title = html.unescape(title)
    
    # 提取公众号名称
    author_match = re.search(r'var nickname = htmlDecode\("([^"]*)"\)', content)
    if not author_match:
        author_match = re.search(r'profile_nickname[^>]*>([^<]+)', content)
    author = author_match.group(1) if author_match else "微信公众号"
    
    # 提取正文
    content_match = re.search(
        r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*</div>',
        content, 
        re.DOTALL
    )
    
    if content_match:
        article_html = content_match.group(1)
    else:
        # 备用方案：查找 rich_media_content
        content_match = re.search(
            r'<div class="rich_media_content[^"]*"[^>]*>(.*?)</div>\s*</div>',
            content,
            re.DOTALL
        )
        article_html = content_match.group(1) if content_match else content
    
    # 清理 HTML
    text = article_html
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    
    # 处理代码块
    text = re.sub(r'<code[^>]*>([^<]+)</code>', r'`\1`', text)
    text = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n```\n\1\n```\n', text, flags=re.DOTALL)
    
    # 处理标题
    text = re.sub(r'<h1[^>]*>([^<]+)</h1>', r'\n# \1\n', text)
    text = re.sub(r'<h2[^>]*>([^<]+)</h2>', r'\n## \1\n', text)
    text = re.sub(r'<h3[^>]*>([^<]+)</h3>', r'\n### \1\n', text)
    text = re.sub(r'<h4[^>]*>([^<]+)</h4>', r'\n#### \1\n', text)
    
    # 处理段落和换行
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    
    # 移除其他 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 解码 HTML 实体
    text = html.unescape(text)
    
    # 清理多余空白
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    text = text.strip()
    
    return {
        'title': title,
        'author': author,
        'content': text
    }

if __name__ == '__main__':
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
    else:
        html_file = '/tmp/wx_article.html'
    
    result = extract_wechat_article(html_file)
    
    print(f"=== 标题 ===\n{result['title']}\n")
    print(f"=== 作者 ===\n{result['author']}\n")
    print(f"=== 正文 ===\n{result['content']}")
```

---

## 使用示例

### 示例 1: 获取单篇文章

用户输入：
```
帮我获取 https://mp.weixin.qq.com/s/xxxxx 发布到博客
```

执行流程：
1. curl 获取 HTML
2. Python 提取标题和正文
3. 整理为博客格式
4. 保存到 `_posts/` 目录
5. git commit && git push

### 示例 2: 指定分类和标签

用户输入：
```
获取这篇公众号文章，分类为 C++，标签为 cpp、性能优化
```

自动设置：
```yaml
categories: [C++, 现代C++]
tags: [cpp, 性能优化]
```

---

## 输出格式

执行完成后，输出摘要：

```
📰 文章获取完成

标题：{文章标题}
作者：{公众号名称}
字数：约 {N} 字

📁 已保存到：_posts/{日期}-{标题}.md
🚀 已推送到 GitHub

访问地址：https://{域名}/{标题}/
```

---

## 注意事项

1. **版权声明**：转载文章务必注明原作者和来源
2. **内容整理**：自动提取的内容可能需要手动调整格式
3. **代码块**：公众号的代码块格式可能丢失，需要手动添加 Markdown 代码块标记
4. **图片处理**：文章中的图片仍然引用公众号 CDN，如需长期保存建议下载到本地
5. **时效性**：公众号文章可能被删除或修改，建议及时保存

---

## 常见问题

### Q: 为什么获取不到内容？

A: 可能的原因：
- 文章已删除
- 文章设置了访问权限
- 网络问题导致 HTML 不完整

解决方法：
- 在浏览器中打开链接确认文章存在
- 检查 curl 输出的 HTML 是否完整

### Q: 格式混乱怎么办？

A: 公众号文章的 HTML 结构不统一，可能需要：
- 手动调整章节标题层级
- 重新格式化代码块
- 添加缺失的换行

### Q: 如何处理数学公式？

A: 公众号的数学公式通常以图片形式存在，需要：
- 手动用 LaTeX 重写公式
- 或保留图片引用

---

## 快速参考

```bash
# 快速获取文章
curl -sL -A "Mozilla/5.0" "URL" > /tmp/wx.html && python3 /tmp/extract_wechat.py

# 查看文章标题
grep -oP 'og:title" content="[^"]*' /tmp/wx.html

# 统计字数
wc -m /tmp/plain_text.txt
```
