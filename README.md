# VPS库存监控系统

![VPS库存监控系统](https://placehold.co/600x300/e6f7ff/1890ff?text=VPS+Stock+Monitor)

## 项目简介

VPS库存监控系统是一个功能完善的库存监控工具，专门设计用于监控VPS、服务器和其他IT产品的库存状态。系统支持多种通知方式，可以帮助您在目标产品有库存时第一时间获得通知，从而不错过心仪的产品。

## 功能特点

### 权限分离
- 管理员可配置监控项和通知方式
- 普通用户仅能查看库存状态

### 多通知方式
- 支持Telegram机器人通知
- 支持微信(息知)通知
- 支持自定义URL通知

### 定时监控
- 可配置监控频率
- 自动检查库存状态
- 状态变化时触发通知

### 防反爬机制
- 集成FlareSolverr代理支持
- 可绕过Cloudflare等防护

### 容器化部署
- 支持Docker和Docker Compose快速部署
- 一键启动，简化运维

### 密码修改
- 管理员可自行修改登录密码
- 提高系统安全性

### 详细日志
- 完善的日志记录
- 便于问题排查和系统监控

## 系统要求

- Docker
- Docker Compose
- 网络连接

## 安装和配置

### 1. 克隆仓库

```bash
git clone https://github.com/YamaDang/vps-stock-monitor.git
cd vps-stock-monitor
```

### 2. 配置环境变量

复制或重命名`.env.example`文件为`.env`，并根据您的需求修改以下配置项：

```env
# Flask配置
SECRET_KEY=your-secret-key
FLASK_ENV=production

# 数据库配置
DATABASE_URL=sqlite:///data/vps_monitor.db

# FlareSolverr配置
FLARESOLVERR_URL=http://flaresolverr:8191/v1

# 管理员账户配置
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password

# 监控配置
DEFAULT_MONITOR_INTERVAL=300  # 默认监控间隔(秒)

# Telegram通知配置 (可选)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# 微信(息知)通知配置 (可选)
XI_ZHI_TOKEN=your-xi-zhi-token
```

### 3. 启动系统

使用提供的启动脚本快速启动系统：

```bash
chmod +x start.sh
./start.sh
```

或者直接使用Docker Compose命令：

```bash
docker-compose up -d --build
```

### 4. 访问系统

启动成功后，您可以通过以下地址访问系统：

```
http://localhost:5000
```

默认管理员账户：
- 用户名：admin (可在.env文件中修改)
- 密码：password (可在.env文件中修改)

## 使用说明

### 管理员功能

1. **监控目标管理**
   - 添加新的监控目标
   - 编辑现有监控目标
   - 启用/禁用监控目标
   - 设置监控间隔
   - 立即检查库存状态

2. **通知设置管理**
   - 添加新的通知配置
   - 编辑现有通知配置
   - 设置通知类型(Telegram/微信/自定义URL)
   - 启用/禁用通知

3. **系统日志查看**
   - 查看系统运行日志
   - 按日志级别筛选
   - 按关键词搜索日志

4. **数据统计分析**
   - 查看监控目标统计信息
   - 监控库存状态分布
   - 查看响应时间趋势

5. **修改密码**
   - 定期修改密码提高安全性

### 普通用户功能

1. **查看库存状态**
   - 浏览所有监控目标的当前状态
   - 查看响应时间和上次检查时间

## 监控目标配置详解

添加监控目标时，您需要设置以下参数：

- **名称**：监控目标的描述性名称
- **URL**：需要监控的网页URL
- **检查类型**：
  - 文本匹配：检查页面中是否包含特定文本
  - CSS选择器：检查特定CSS选择器的元素内容
  - API响应：解析JSON/XML格式的API响应
- **检查模式**：
  - 有库存时：当检测到特定内容时标记为有库存
  - 无库存时：当检测到特定内容时标记为无库存
- **检查内容**：根据检查类型设置相应的文本、CSS选择器或JSON路径
- **监控间隔**：检查频率(秒)

## 通知配置详解

添加通知设置时，您需要设置以下参数：

- **监控目标**：选择要接收通知的监控目标
- **通知类型**：
  - Telegram：通过Telegram机器人发送通知
  - 微信(息知)：通过微信(息知)服务发送通知
  - 自定义URL：向指定URL发送HTTP请求
- **配置信息**：根据通知类型设置相应的Token、Chat ID或URL
- **启用通知**：开关通知功能

## 常见问题

### Q: 如何获取Telegram Bot Token和Chat ID？

A: 您可以通过与@BotFather对话创建Telegram机器人获取Token，然后使用@userinfobot获取Chat ID。

### Q: 微信(息知)是什么？如何使用？

A: 息知是一个提供微信通知服务的平台，您可以访问https://xizhi.qqoq.net注册并获取Token。

### Q: FlareSolverr有什么作用？

A: FlareSolverr用于绕过网站的Cloudflare等反爬机制，确保监控正常运行。

### Q: 如何修改默认监控间隔？

A: 您可以在.env文件中修改`DEFAULT_MONITOR_INTERVAL`参数。

### Q: 如何查看系统日志？

A: 您可以通过Web界面的"系统日志"功能查看，或者使用命令：
```bash
docker-compose logs -f app
```

## 系统架构

系统由两个主要组件组成：

1. **主应用**：基于Flask的Web应用，提供用户界面和监控逻辑
2. **FlareSolverr**：用于绕过反爬机制的代理服务

数据存储使用SQLite数据库，默认保存在`data/vps_monitor.db`文件中。

## 开发指南

如果您想参与项目开发，可以按照以下步骤进行：

1. 克隆仓库并进入项目目录
2. 安装Python依赖：`pip install -r requirements.txt`
3. 创建并配置.env文件
4. 启动Flask开发服务器：`flask run`
5. 启动FlareSolverr服务：使用Docker或直接运行

## 部署指南

### Docker Compose部署

项目提供了完整的Docker Compose配置，是推荐的部署方式：

```bash
docker-compose up -d --build
```

### 手动部署

1. 安装Python 3.9或更高版本
2. 安装依赖：`pip install -r requirements.txt`
3. 配置.env文件
4. 启动Flask应用：`gunicorn --bind 0.0.0.0:5000 app:app`
5. 确保FlareSolverr服务正常运行

## 安全建议

1. 定期修改管理员密码
2. 不要在公共网络中使用弱密码
3. 考虑使用HTTPS加密通信
4. 定期备份数据库文件
5. 限制对管理界面的访问

## License

[MIT](LICENSE)
