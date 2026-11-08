<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

# nonebot-plugin-R6States

基于 **NoneBot2** 的《彩虹六号：围攻》战绩查询插件

## Feature 功能特性

* ✅ 通过指令查询**单人 / 多人** R6 玩家战绩
* ✅ 数据源自 [R6Data API](https://r6.arenyze.com/)
* ✅ 玩家数据缓存，图片左下角显示更新时间，右下角显示查询赛季
* ✅ 模式战绩卡片、攻防干员 Top 4 与出场比例条，使用本地字体离线绘图

## Usage 使用说明

### 安装

- （推荐）使用nb安装`nb plugin install nonebot-plugin-R6States`
- 使用pip安装`pip install nonebot-plugin-R6States`
- 下载release放到`plugins`文件夹中

### 指令

数据查询：`/R6 <player_ids...>`
其他指令与帮助信息：`/R6help`

## 环境配置

```
CURRENT_SEASON = "Y11S3"
R6_OUTPUT_IMAGE = True
R6_CACHE_MINUTES = 45
```

## Environment 参考运行环境

* **Python 3.12**
* **NoneBot2**
* **OneBot v11**
* **NapCat（反向 WebSocket）**

## Notice 特别提醒

* 本插件为 **非育碧官方工具**
* 所有数据来自R6Data API
* 设计初衷仅对于个人与学习
* 请勿用于“超出个人正常使用范围”的用途

## 录像分析

发送 `/r6 analyze`，并在**同一条消息**中附上 `.rec` 文件。
支持 1–20 个同一场比赛的录像文件，默认附件总大小上限为 128 MB，
可用 `R6_REPLAY_MAX_MB` 调整。回复消息中的附件或后续单独发送的文件不会被读取。

机器人使用现有的个人/群 API Key，将录像上传至 Arenyze，返回地图、模式、
比分、回合数、玩家数、总击杀和剩余存储额度。可用 `/r6key <key>` 设置 Key。
上传后录像会占用该 Key 对应账户的 Arenyze 存储额度。

需要 OneBot/NapCat 能在消息中提供文件段，并支持附件下载地址。
若 QQ 客户端将文件作为单独的上传通知发送，机器人会提示需要同一消息附件。

内部 API 封装对齐 `r6-data.js` 3.3.1（上游提交
`544eff7536bb89acbf0ca1e9a654191120ccdcf9`）。
