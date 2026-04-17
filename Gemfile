# frozen_string_literal: true

source "https://rubygems.org"

# jekyll-theme-yat 的样式使用 @use / sass:meta（Dart Sass）。github-pages 固定 Jekyll 3.9 +
# jekyll-sass-converter 1.x，无法编译该主题；GitHub Actions 自建环境用 Jekyll 4 即可。
gem "jekyll", "~> 4.3"
gem "jekyll-sass-converter", "~> 3.0"

group :jekyll_plugins do
  gem "jekyll-remote-theme"
  gem "jekyll-feed"
  gem "jekyll-seo-tag"
  gem "jekyll-sitemap"
  gem "jekyll-paginate"
  gem "jekyll-spaceship", "~> 0.10"
end

gem "webrick", "~> 1.8"
