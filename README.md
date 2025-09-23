# VPS库存监控系统

一个功能完善的库存监控工具，特别适用于监控VPS等产品的库存状态，支持多种通知方式，并实现了管理员与普通用户的权限分离。

## 功能特点

- **权限分离**：管理员可配置监控项和通知方式，普通用户仅能查看库存状态
- **多通知方式**：支持Telegram、微信(息知)和自定义URL通知
- **定时监控**：可配置监控频率，自动检查库存状态
- **防反爬机制**：集成FlareSolverr代理支持，可绕过Cloudflare等防护
- **容器化部署**：支持Docker和Docker Compose快速部署
- **密码修改**：管理员可自行修改登录密码，提高安全性
- **详细日志**：完善的日志记录，便于问题排查

## 部署方式

### Docker Compose (推荐)

1. 克隆仓库
   ```bash
   git clone https://github.com/yourusername/vps-stock-monitor.git
   cd vps-stock-monitor
   ```

2. 配置环境变量
   ```bash
   cp .env.example .env
   # 编辑.env文件，至少修改SECRET_KEY为随机安全字符串
   # 生成安全密钥的方法：openssl rand -hex 16
   ```

3. 启动服务
   ```bash
   docker-compose up -d
   ```

4. 访问系统
   - 公共展示页面: http://localhost:5000
   - 管理员登录: http://localhost:5000/login (默认账号: admin, 密码: admin123)

### 手动部署

1. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

2. 配置环境变量
   ```bash
   cp .env.example .env
   # 编辑.env文件设置必要参数
   ```

3. 初始化并启动
   ```bash
   # 加载环境变量
   export $(cat .env | xargs)
   # 启动应用
   python web.py
   ```

## 首次使用指南

1. 访问管理员登录页面（http://localhost:5000/login）
2. 使用默认账号密码登录：admin/admin123
3. **重要**：登录后立即前往"个人设置"修改默认密码
4. 在"系统设置"中配置通知方式：
   - Telegram：需要Bot Token和Chat ID
   - 微信：需要息知KEY（可在https://xizhi.qqoq.net/获取）
   - 自定义URL：设置包含{message}占位符的通知URL
5. 在"监控列表"中添加需要监控的商品URL
6. 系统将自动开始监控，并在库存变化时发送通知

## 安全提示

- 生产环境中务必修改默认密码
- 更换SECRET_KEY为强随机字符串（可使用`openssl rand -hex 16`生成）
- 考虑使用反向代理（如Nginx）配置HTTPS
- 定期备份data目录下的配置文件和instance目录下的数据库文件

## 项目结构vps-stock-monitor/
├── core.py               # 库存监控核心逻辑
├── web.py                # Flask Web应用主程序
├── models.py             # 用户数据模型
├── auth.py               # 认证与权限控制功能
├── requirements.txt      # 项目依赖列表
├── Dockerfile            # Docker构建文件
├── docker-compose.yml    # Docker Compose配置
├── .env.example          # 环境变量示例
├── data/                 # 配置文件和日志存储目录
├── instance/             # 数据库文件存储目录
└── templates/            # 前端模板
    ├── login.html        # 登录页面
    ├── public/           # 公共页面
    │   └── index.html    # 库存状态展示页面
    └── admin/            # 管理员页面
        ├── index.html    # 管理员控制台
        └── profile.html  # 个人设置页面
## 常见问题

1. **无法访问系统**
   - 检查Docker容器是否正常运行：`docker-compose ps`
   - 检查端口是否被占用：`netstat -tulpn | grep 5000`
   - 检查防火墙设置，确保5000端口已开放

2. **通知无法发送**
   - 检查通知配置是否正确
   - 查看日志文件：`data/app.log` 和 `data/monitor.log`
   - 测试通知配置是否有效（如Telegram可直接调用API测试）

3. **数据库相关错误**
   - 确保instance目录有正确的权限：`chmod -R 777 instance/`
   - 检查数据库文件是否存在：`instance/users.db`

## 许可证

MIT
