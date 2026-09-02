# 秒回 MiaoHui

> 你的电脑里的一切，0.3 秒找回 —— 本地、离线、可审计的新一代搜索引擎。

按 **⌥Space** 唤起，用一句话描述，直接命中照片/截图/录屏/视频里的那一帧，
并跳回原文件、原视频的精确时间点（第 12 分 34 秒）。

## 它解决什么

几十万张照片、截图、录屏、视频散落在桌面/下载/微信/相册里。
Finder 按文件名搜、照片 App 按时间翻——**都没有按"内容"搜**。

秒回把每一张图、每一帧视频画面、每一段语音全部变成可检索的知识：

| 通道 | 技术 | 能搜到什么 |
|------|------|-----------|
| 视觉 | Chinese-CLIP 图文向量（512d HNSW） | "红衣服跳舞的画面"、"白色显卡开箱" |
| 文字 | Apple Vision OCR（简繁中文） | 图片/视频画面里的每一行字 |
| 语音 | faster-whisper ASR（带时间戳） | 视频里说过的每一句话 |

三路召回 + RRF 融合排序，全程本地计算，**断网也能用**。

## 信任模型（第一天的设计，不是补丁）

这个品类的死法只有两种：偷偷上传、本地库裸奔。秒回从第一行代码就不同：

1. **零网络** —— 引擎不含任何网络代码，可审计（`grep -r "requests\|urllib\|socket" core/`）
2. **敏感排除** —— 银行/密码/钥匙串/身份证关键词目录一律不索引，默认开启
3. **加密存储** —— 缩略图 AES-256-GCM 加密，密钥在你自己的 macOS 钥匙串
4. **完全透明** —— `audit.jsonl` 记录每一个被索引/被排除的文件，一键打开
5. **秒级反悔** —— 索引目录整体可删，删除即消失，无云端残留

## 架构

```
core/
  scanner.py   扫描器（敏感排除剪枝）
  frames.py    视频帧采样（关键帧选点 + 静止去重）+ 16k 音频提取
  ocr.py       Apple Vision OCR
  asr.py       faster-whisper int8
  embed.py     Chinese-CLIP + bge-small-zh（ONNX, CPU）
  db.py        SQLite + FTS5(jieba) + hnswlib 双索引
  search.py    三路召回 RRF 融合
  security.py  AES-GCM 加密 + Keychain + 审计
  pipeline.py  索引管线（独立进程，增量）
app/
  panel.py     ⌥Space 面板（原生 AppKit HUD 毛玻璃）
  menubar.py   菜单栏（状态/暂停/审计入口）
  hotkey.py    Carbon 全局热键
  opener.py    原文件跳转（视频精确到秒）
```

## 运行

```bash
python3 scripts/download_models.py   # 首次：下载模型（HF 镜像）
python3 main.py --index              # 构建索引
python3 main.py                      # 启动：菜单栏 + ⌥Space
python3 main.py --search "白色显卡"  # 命令行检索（含耗时分解）
```

## 性能（Apple M1, 8GB）

- 查询端到端：**0.15 ~ 0.30s**（CLIP 文本 15ms + bge 10ms + HNSW 5ms + FTS 10ms）
- 索引速度：图片 ~35 张/分钟（OCR+嵌入）；视频 ~2.5x 实时（帧+语音双通道）

## License

MIT
