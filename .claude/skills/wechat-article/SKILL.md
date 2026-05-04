---
name: wechat-article
description: 获取微信公众号文章内容并发布到博客。当用户提供公众号文章链接时，自动提取文章标题和正文，整理为博客文章格式。
license: MIT
compatibility: 适用于 Jekyll 博客
metadata:
  author: WorkGuide
  version: "1.1"
---

# 微信公众号文章获取 Skill

从微信公众号文章链接提取内容，整理为标准博客文章格式，并发布到 Jekyll 博客的 `_posts` 目录。

---

## 触发条件

**必须使用此 skill 当：**
- 用户提供微信公众号文章链接（`mp.weixin.qq.com/s/...`）
- 用户说"帮我获取这篇公众号文章"
- 用户说"把这个公众号文章发到博客"

---

## 博客目录结构

**重要**：博客文章必须放在 `_posts` 目录下，不能直接放在 `blog/` 根目录。

```
blog/
├── _posts/                    # 博客文章存放位置（必须）
│   ├── 2026-05-04-article-title.md
│   ├── 2026-05-05-another-article.md
│   └── ...
├── _config.yml               # Jekyll 配置
├── index.html                # 首页
└── ...                       # 其他 Jekyll 文件
```

### 文件命名规范

Jekyll 要求文章文件名格式：`YYYY-MM-DD-title.md`

- 日期：使用当前日期（文章发布日期）
- 标题：**使用中文标题**，直接从文章提取的原标题
- 示例：`2026-05-04-一次memcpy干掉整条虚函数表.md`

**注意**：Jekyll 完全支持中文文件名，无需转换为英文或拼音。保留中文标题有利于 SEO 和可读性。

---

## 提取方法

### 实际可用的提取流程

经过验证，以下方法可以有效提取微信公众号文章：

#### Step 1: 下载文章 HTML

```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://mp.weixin.qq.com/s/xxxxx" > /tmp/wx_article.html
```

#### Step 2: 提取标题

```bash
# 方法 1: 从 js_title_inner span 提取（推荐）
grep -oP '(?<=<span class="js_title_inner">)[^<]+' /tmp/wx_article.html

# 方法 2: 从 activity-name h1 提取
grep -oP '(?<=id="activity-name">)[^<]+' /tmp/wx_article.html | head -1
```

#### Step 3: 提取正文内容

```bash
# 提取 js_content div 内容
sed -n '/<div class="rich_media_content/,/<\/div>/p' /tmp/wx_article.html | head -n -1 > /tmp/article_content.html
```

#### Step 4: HTML 转 Markdown

使用 Python 处理 HTML 并转换为 Markdown：

```python
import re
import html

def html_to_markdown(html_content):
    """将微信文章 HTML 转换为 Markdown"""
    
    # 移除脚本和样式
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    
    # 处理代码块（必须在其他转换之前）
    text = re.sub(r'<pre[^>]*>', '\n```\n', text)
    text = re.sub(r'</pre>', '\n```\n', text)
    text = re.sub(r'<code[^>]*>', '`', text)
    text = re.sub(r('</code>)', '`', text)
    
    # 处理标题
    text = re.sub(r'<h1[^>]*>([^<]+)</h1>', r'\n# \1\n', text)
    text = re.sub(r'<h2[^>]*>([^<]+)</h2>', r'\n## \1\n', text)
    text = re.sub(r'<h3[^>]*>([^<]+)</h3>', r'\n### \1\n', text)
    
    # 处理强调
    text = re.sub(r'<strong[^>]*>([^<]+)</strong>', r'**\1**', text)
    text = re.sub(r'<b[^>]*>([^<]+)</b>', r'**\1**', text)
    text = re.sub(r'<em[^>]*>([^<]+)</em>', r'*\1*', text)
    
    # 处理段落和换行
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'</section>', '\n', text)
    text = re.sub(r'</div>', '\n', text)
    
    # 处理列表
    text = re.sub(r'<li[^>]*>', '- ', text)
    text = re.sub(r'</li>', '\n', text)
    
    # 移除剩余 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 解码 HTML 实体
    text = html.unescape(text)
    
    # 清理多余空白
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    
    return text
```

#### Step 5: 提取公众号名称

```bash
# 从 js_name 提取
grep -oP '(?<=id="js_name">)[^<]+' /tmp/wx_article.html | head -1
```

---

## 文章格式

生成的博客文章需包含完整的 YAML Front Matter：

```markdown
---
title: 文章标题
tags: [标签1, 标签2, 标签3]
created: YYYY-MM-DD HH:MM:SS
updated: YYYY-MM-DD HH:MM:SS
source: 原文链接
author: 公众号名称
---

# 文章标题

[文章正文内容，转换为 Markdown 格式]

---

> 原文链接：[公众号名称](原文URL)
```

### 标签推断规则

根据文章内容自动推断标签：

| 内容特征 | 推断标签 |
|----------|----------|
| 包含 C++、cpp、虚函数、模板等 | `cpp` `内存` `性能` |
| 包含 Go、goroutine、channel 等 | `go` `并发` |
| 包含 Linux、内核、系统调用等 | `linux` `内核` |
| 包含 网络、TCP、HTTP 等 | `网络` `TCP` |
| 包含 MySQL、Redis、数据库等 | `数据库` `mysql` `redis` |

---

## 完整执行步骤

### Step 1: 获取文章 HTML

```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "{文章URL}" > /tmp/wx_article.html
```

### Step 2: 提取关键信息

```bash
# 标题
TITLE=$(grep -oP '(?<=<span class="js_title_inner">)[^<]+' /tmp/wx_article.html)

# 公众号名称
AUTHOR=$(grep -oP '(?<=id="js_name">)[^<]+' /tmp/wx_article.html | head -1)
```

### Step 3: 转换正文

```bash
# 提取正文区域
sed -n '/<div class="rich_media_content/,/<\/div>/p' /tmp/wx_article.html > /tmp/content.html

# Python 转换为 Markdown
python3 << 'EOF'
import re
import html

with open('/tmp/content.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 转换逻辑（见上文）
# ...
print(markdown_content)
EOF
```

### Step 4: 生成文件名

```bash
# 当前日期
DATE=$(date +%Y-%m-%d)

# 使用原标题（中文）
TITLE=$(grep -oP '(?<=<span class="js_title_inner">)[^<]+' /tmp/wx_article.html)

# 清理标题中的特殊字符（保留中文、字母、数字、连字符）
SLUG=$(echo "$TITLE" | sed 's/[\/\\:*?"<>|]/-/g' | head -c 80)

FILENAME="${DATE}-${SLUG}.md"
```

**标题优化建议**：
- 可以根据文章内容总结一个更简洁、更准确反映核心主题的标题
- 原标题通常较长且包含"吸引眼球"的修辞，可精简为技术性描述
- 示例：原标题「一次 memcpy 干掉整条虚函数表——拆解 vptr 在继承链上的内存映射」可简化为「memcpy与虚函数表：vptr内存布局解析」

### Step 5: 写入 _posts 目录

**正确路径**：`blog/_posts/YYYY-MM-DD-title.md`

```bash
cat > "blog/_posts/${FILENAME}" << 'EOF'
---
title: {标题}
tags: [{标签}]
created: {时间}
updated: {时间}
source: {原文URL}
author: {公众号名称}
---

# {标题}

{正文内容}

---

> 原文链接：[{公众号名称}]({原文URL})
EOF
```

**错误路径**：~~`blog/YYYY-MM-DD-title.md`~~ （不要放在 blog 根目录）

### Step 6: 更新 INDEX.md（可选）

如果知识库需要索引该文章，更新 INDEX.md：
1. 在相应章节添加条目
2. 更新关键词索引

---

## 使用示例

### 示例：获取并发布文章

用户输入：
```
https://mp.weixin.qq.com/s/r9ssVVPXs22GGLmdGaQVuw 将这篇文章整理下来发布到博客
```

执行流程：
1. curl 下载 HTML 到 `/tmp/wx_article.html`
2. 提取标题：「一次 memcpy 干掉整条虚函数表——拆解 vptr 在继承链上的内存映射」
3. 提取公众号：「C加加玩家请就位」
4. Python 转换正文为 Markdown
5. 生成文件名：`2026-05-04-一次memcpy干掉整条虚函数表.md`（使用中文标题）
6. 保存到 `blog/_posts/2026-05-04-一次memcpy干掉整条虚函数表.md`

输出：
```
📰 文章已发布到博客

标题：一次 memcpy 干掉整条虚函数表——拆解 vptr 在继承链上的内存映射
作者：C加加玩家请就位
文件：blog/_posts/2026-05-04-memcpy-vptr-vtable.md
```

---

## 注意事项

1. **目录正确**：文章必须放在 `blog/_posts/` 目录，不是 `blog/` 根目录
2. **文件名格式**：必须符合 Jekyll 要求 `YYYY-MM-DD-title.md`，使用中文标题
3. **标题优化**：可根据文章内容总结更简洁准确的标题，不必使用原标题
4. **版权声明**：保留原文链接和作者信息
5. **内容完整性**：尽量保留原文的代码、图片、格式
6. **标签提取**：从文章内容推断合适的标签
7. **图片处理**：文章图片仍引用微信 CDN，长期保存建议下载到本地

---

## 错误处理

| 问题 | 解决方案 |
|------|----------|
| 无法访问链接 | 告知用户微信链接有访问限制，请求用户复制内容 |
| 标题提取失败 | 尝试其他提取方法，或让用户提供标题 |
| 内容为空 | 检查 HTML 结构变化，调整 sed/grep 模式 |
| `_posts` 目录不存在 | 创建目录：`mkdir -p blog/_posts` |
| WebFetch 被拦截 | 使用 curl 方法替代 |

---

## 快速参考

```bash
# _posts 目录路径
blog/_posts/

# 文件命名格式（使用中文标题）
YYYY-MM-DD-中文标题.md

# 示例
2026-05-04-一次memcpy干掉整条虚函数表.md

# curl 请求模板
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "微信文章URL" > /tmp/wx_article.html

# 提取标题
grep -oP '(?<=<span class="js_title_inner">)[^<]+' /tmp/wx_article.html

# 提取正文
sed -n '/<div class="rich_media_content/,/<\/div>/p' /tmp/wx_article.html
```
