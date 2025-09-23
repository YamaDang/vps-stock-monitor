# VPS库存监控系统

一个用于监控商品库存状态的工具，支持多种通知方式，并有权限分离的前后端界面。

## 功能特点

- 分离的前后端权限：管理员可配置监控项和通知方式，普通用户仅能查看库存状态
- 多通知方式：支持Telegram、微信(息知)和自定义URL通知
- 定时监控：可配置监控频率，自动检查库存状态
- 容器化部署：支持Docker和Docker Compose快速部署
- 防反爬机制：可配置代理绕过Cloudflare等防护

## 部署方式

### Docker Compose (推荐)

1. 克隆仓库
   ```bash
   git clone https://github.com/yourusername/vps-stock-monitor.git
   cd vps-stock-monitor
   ```

2. 编辑docker-compose.yml，修改SECRET_KEY为随机安全字符串

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

2. 初始化并启动
   ```bash
   python web.py
   ```

## 首次使用

1. 登录管理员界面（默认账号密码：admin/admin123）
2. 立即修改管理员密码（未来版本将添加此功能）
3. 在"系统设置"中配置通知方式
4. 在"监控列表"中添加需要监控的商品URL
5. 系统将自动开始监控，并在库存变化时发送通知

## 安全提示

- 生产环境中务必修改默认密码
- 更换SECRET_KEY为强随机字符串
- 考虑使用反向代理配置HTTPS
- 定期备份data目录下的配置文件

## 许可证

MIT
