# nonebot-plugin-R6States

🎮 一个基于 **NoneBot2 + Playwright** 的《彩虹六号：围攻》战绩查询插件

---

## ✨ 功能特性

* ✅ 通过 QQ 指令查询 R6 玩家战绩
* ✅ 支持 **单人查询 / 多人查询**
* ✅ 使用 **Playwright** 获取完整网页 HTML
* ✅ 使用 **BeautifulSoup** 解析页面结构
* ⚙️ 数据分析功能
* ⚙️ 地图筛选 `-m / --map`

---

## 🧱 参考运行环境

* **Python 3.12**
* **NoneBot2**
* **OneBot v11**
* **NapCat（反向 WebSocket）**
* **Playwright（Chromium）**

---

## 📌 Usage 使用说明

### 安装

可以直接将 `nonebot_plugin_R6States` 文件夹放入插件目录中。

### 基础指令

```text
/R6 <player_id>
```

### 多人查询

```text
/R6 -g <id1> <id2> ... <idN>
```

### 帮助信息

```text
/R6 -h
/R6 --help
```

### 额外获取地图信息

```text
-m / --map <map_name>
```

---

## ⚠️ 相关问题

### Q1：为什么要使用 Playwright ？

* 以前R6Tracker的页面是静态的，使用 requests 即可获取完整数据
* 现在页面改成了动态渲染，直接请求无法获得数据

### Q2：为什么多人查询耗时很久？

* R6Tracker官方并未提供API，获取数据的过程本质是爬虫
* 虽然短时间查询一定数量数量的玩家的数据是正常行为，但考虑到TRN在官网写道不允许爬虫，或许数据时没有使用并发
* 页面中有部分内容加载速度较慢，需要等待数据完全加载

### Q3：查询的原理？

* 对于基础数据的查询用的是R6Data的API，对于地图等更多数据暂时使用R6Tracker

---

## 📜 免责声明

* 本插件为 **非官方工具**
* 所有数据来自公开网页
* 仅用于学习与个人使用
* Tracker Network官方**并未提供**R6S的API
* 请勿用于任何“超出个人正常使用范围”的用途
* 高频请求可能会导致被TRN封禁
