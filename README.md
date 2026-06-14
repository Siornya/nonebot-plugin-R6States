# nonebot-plugin-R6States

一个基于 **NoneBot2** 的《彩虹六号：围攻》战绩查询插件

## 功能特性

* ✅ 通过 QQ 指令查询 R6 玩家战绩
* ✅ 支持 **单人查询 / 多人查询**
* ✅ 数据源自 [R6Data API](https://r6data.com/)
* ✅ 玩家数据缓存，降低 API 用量
* ✅ 数据分析功能
* ⚙️ 地图筛选 `-m / --map`

## Usage 使用说明

### 安装

- （推荐）使用nb安装`nb plugin install nonebot-plugin-R6States`
- 使用pip安装`pip install nonebot-plugin-R6States`
- 下载release放到`plugins`文件夹中

### 指令

数据查询：`/R6 <player_ids...>`
其他指令与帮助信息：`/R6help`

## 环境配置

CURRENT_SEASON = "Y11S2"

R6_OUTPUT_IMAGE = True

R6_CACHE_MINUTES = 45

## 参考运行环境

* **Python 3.12**
* **NoneBot2**
* **OneBot v11**
* **NapCat（反向 WebSocket）**

## 特别提醒

* 本插件为 **非育碧官方工具**
* 所有数据来自R6Data API
* 设计初衷仅对于个人与学习
* 请勿用于“超出个人正常使用范围”的用途
