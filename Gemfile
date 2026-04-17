# frozen_string_literal: true

source "https://rubygems.org"

# 已包含 jekyll-remote-theme 等与 Pages 对齐的版本：https://pages.github.com/versions/
group :jekyll_plugins do
  gem "github-pages"
  gem "jekyll-spaceship", "~> 0.10"
end

# Ruby 3+ 本地 `jekyll serve` 需要；GitHub Actions 仅 build 时可忽略
gem "webrick", "~> 1.8"