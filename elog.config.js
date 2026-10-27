// 飞书云文档 → Jekyll 博客。由 .github/workflows/feishu-sync.yml 定时运行。
// 凭证从仓库 Secrets 注入，本地调试用 `npx @elog/cli@0.14.7 sync -e .elog.env`。
module.exports = {
  write: {
    platform: 'feishu',
    feishu: {
      // 'space'：同步「我的空间」里某个文件夹；'wiki'：同步某个知识库
      type: process.env.FEISHU_TYPE || 'space',
      folderToken: process.env.FEISHU_FOLDER_TOKEN,
      wikiId: process.env.FEISHU_WIKI_ID,
      appId: process.env.FEISHU_APP_ID,
      appSecret: process.env.FEISHU_APP_SECRET,
    },
  },
  deploy: {
    platform: 'local',
    local: {
      // Elog 的原始输出；.github/scripts/feishu-to-posts.sh 再把它整理成 _posts/feishu/
      outputDir: './_feishu',
      // 用飞书文档 id 当文件名，改标题不会产生重复文章
      filename: 'urlname',
      format: 'markdown',
      frontMatter: { enable: true },
    },
  },
  image: {
    // 飞书图片链接会过期，下载到仓库里
    enable: true,
    platform: 'local',
    local: {
      outputDir: './assets/feishu',
      prefixKey: '/assets/feishu',
    },
  },
}
