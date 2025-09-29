# VPS库存监控系统

![VPS库存监控系统](https://placehold.co/600x300/e6f7ff/1890ff?text=VPS+Stock+Monitor)

## 项目简介

VPS库存监控系统是一款功能完善的自动化监控工具，专为追踪VPS、服务器和其他IT产品的库存状态而设计。系统支持多种监控方式和通知渠道，帮助用户在目标产品有库存时第一时间获得通知，不错过心仪的产品。

## 功能特点

### 🔐 权限分离
- 管理员可配置监控项和通知方式
- 普通用户仅能查看库存状态

### 📬 多通知方式
- 支持Telegram机器人通知
- 支持微信(息知)通知
- 支持自定义URL通知

### ⏱️ 定时监控
- 可配置监控频率
- 自动检查库存状态
- 状态变化时触发通知

### 🛡️ 防反爬机制
- 集成FlareSolverr代理支持
- 可绕过Cloudflare等防护

### 🐳 容器化部署
- 支持Docker和Docker Compose快速部署
- 一键启动，简化运维

### 🔑 密码修改
- 管理员可自行修改登录密码
- 提高系统安全性

### 📊 数据统计与日志
- 完善的日志记录系统
- 响应时间统计与可视化
- 库存状态分布分析
- 便于问题排查和系统监控

### 📱 现代化界面
- 响应式设计，支持各种设备访问
- 简洁明了的操作界面
- 实时状态显示和通知管理

### 🎯 多类型监控
- 文本匹配监控
- CSS选择器监控
- API响应监控
- 灵活的监控模式配置

## 系统架构

系统由以下主要组件构成：

1. **主应用**：基于Flask的Web应用，提供用户界面和核心监控逻辑
2. **FlareSolverr**：用于绕过反爬机制的代理服务
3. **SQLite数据库**：轻量级数据存储，保存监控配置和历史数据

## 系统要求

- Docker和Docker Compose（推荐部署方式）
- 或Python 3.9+环境（开发环境）
- 稳定的网络连接

## 安装和配置

### 1. 克隆仓库

```bash
# 克隆项目仓库
git clone https://github.com/yourusername/vps-stock-monitor.git
cd vps-stock-monitor
```

### 2. 配置环境变量

项目包含`.env`文件用于环境配置。请确保文件中包含以下必要配置：

```env
# Flask配置
SECRET_KEY=your-secret-key  # 建议使用随机生成的密钥
FLASK_ENV=production        # 生产环境设为production

# 数据库配置
DATABASE_URL=sqlite:///data/vps_monitor.db

# FlareSolverr配置
FLARESOLVERR_URL=http://flaresolverr:8191/v1

# 管理员账户配置
ADMIN_USERNAME=admin        # 管理员用户名
ADMIN_PASSWORD=password     # 管理员密码（首次登录后请修改）

# 监控配置
DEFAULT_MONITOR_INTERVAL=300  # 默认监控间隔(秒)

# Telegram通知配置 (可选)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# 微信(息知)通知配置 (可选)
XI_ZHI_TOKEN=your-xi-zhi-token
```

### 3. 启动系统

#### 使用启动脚本（推荐）

```bash
chmod +x start.sh
./start.sh
```

#### 使用Docker Compose命令

```bash
docker-compose up -d --build
```

### 4. 访问系统

启动成功后，通过以下地址访问系统：

```
http://localhost:5000
```

首次登录后，请立即修改管理员密码以确保系统安全。

## 使用说明

### 管理员功能

1. **监控目标管理**
   - 添加、编辑、删除监控目标
   - 启用/禁用监控目标
   - 设置监控间隔和检查方式
   - 手动触发立即检查
   - 配置防反爬选项

2. **通知设置管理**
   - 添加多种类型的通知配置
   - 管理通知触发条件
   - 启用/禁用特定通知

3. **系统日志查看**
   - 实时查看系统运行日志
   - 按级别和关键词筛选日志
   - 监控系统健康状态

4. **数据统计分析**
   - 查看库存状态分布统计
   - 分析监控目标响应时间趋势
   - 了解系统运行状况

5. **密码管理**
   - 修改管理员账户密码

### 普通用户功能

1. **查看库存状态**
   - 浏览所有监控目标的当前状态
   - 查看响应时间和上次检查时间
   - 了解产品库存变化情况

## 监控目标配置详解

添加或编辑监控目标时，需要配置以下参数：

- **名称**：监控目标的描述性名称（如：搬瓦工DC9服务器）
- **URL**：需要监控的产品页面URL
- **检查类型**：
  - **文本匹配**：检查页面中是否包含特定文本内容
  - **CSS选择器**：检查特定CSS选择器对应的元素是否存在或包含特定内容
  - **API响应**：解析JSON/XML格式的API响应内容
- **检查模式**：
  - **有库存时**：当检测到特定内容时，标记为产品有库存
  - **无库存时**：当检测到特定内容时，标记为产品无库存
- **检查内容**：根据选择的检查类型，填写相应的文本、CSS选择器或JSON路径
- **监控间隔**：设定自动检查的时间间隔（秒），默认300秒
- **使用FlareSolverr**：是否启用反爬绕过功能

## 通知配置详解

添加或编辑通知设置时，需要配置以下参数：

- **监控目标**：选择要接收通知的监控目标（可多选）
- **通知类型**：
  - **Telegram**：通过Telegram机器人发送通知
  - **微信(息知)**：通过微信息知服务发送通知
  - **自定义URL**：向指定URL发送HTTP请求（可用于集成其他系统）
- **配置信息**：根据选择的通知类型，填写相应的配置参数
  - Telegram：Bot Token和Chat ID
  - 微信(息知)：Token
  - 自定义URL：目标URL
- **启用通知**：开关此通知配置的功能

## 常见问题解答

### Q: 如何获取Telegram Bot Token和Chat ID？

A: 您可以通过以下步骤获取：
1. 在Telegram中与@BotFather对话创建新机器人，获取Token
2. 使用@userinfobot获取您的Chat ID
3. 将获取的信息填入.env文件中

### Q: 微信(息知)是什么？如何使用？

A: 息知是一个提供微信消息推送服务的平台，您可以：
1. 访问https://xizhi.qqoq.net注册账号
2. 获取个人Token
3. 将Token填入.env文件中启用微信通知

### Q: FlareSolverr有什么作用？

A: FlareSolverr是一个用于绕过网站反爬机制的代理服务，主要用于：
- 解决Cloudflare等防护系统的验证码问题
- 模拟真实浏览器行为，避免被识别为爬虫
- 确保监控请求能够正常访问目标网站

### Q: 如何修改默认监控间隔？

A: 您可以在.env文件中修改`DEFAULT_MONITOR_INTERVAL`参数，单位为秒。

### Q: 如何查看系统日志？

A: 您可以通过两种方式查看系统日志：
1. Web界面：登录系统后，进入"系统日志"功能查看
2. 命令行：使用`docker-compose logs -f app`命令实时查看

### Q: 数据存储在哪里？如何备份？

A: 系统使用SQLite数据库，默认存储在`data/vps_monitor.db`文件中。备份时只需复制此文件即可。

## 开发指南

如果您想参与项目开发或进行自定义修改，可以按照以下步骤进行：

1. 克隆仓库并进入项目目录
2. 安装Python依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 复制并配置.env文件
4. 启动Flask开发服务器：
   ```bash
   flask run
   ```
5. 启动FlareSolverr服务（可使用Docker）

## 部署指南

### Docker Compose部署（推荐）

项目提供了完整的Docker Compose配置，是最简单的部署方式：

```bash
docker-compose up -d --build
```

### 手动部署

1. 安装Python 3.9或更高版本
2. 安装项目依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 配置.env文件
4. 启动Flask应用（生产环境推荐使用Gunicorn）：
   ```bash
   gunicorn --bind 0.0.0.0:5000 app:app
   ```
5. 确保FlareSolverr服务正常运行

## 安全建议

为确保系统安全稳定运行，请遵循以下建议：

1. **定期修改密码**：尤其是管理员账户密码
2. **使用强密码**：包含大小写字母、数字和特殊字符
3. **数据备份**：定期备份数据库文件以防丢失
4. **访问控制**：在生产环境中，考虑限制对管理界面的访问
5. **HTTPS配置**：在生产环境中，建议配置HTTPS加密通信
6. **环境变量保护**：不要将包含敏感信息的.env文件提交到代码仓库

## 许可证

本项目采用[MIT许可证](LICENSE)。

## 更新日志

### 最新版本
- 添加浏览器标签图标(favicon)
- 优化监控目标管理页面的滚动体验
- 改进响应时间数据显示格式

### 历史版本
- 实现基本监控功能和通知系统
- 添加防反爬机制支持
- 完善数据统计和可视化
- 支持容器化部署

---

感谢您使用VPS库存监控系统！如有任何问题或建议，欢迎提交Issue或Pull Request。