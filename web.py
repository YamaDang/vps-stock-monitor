from flask import Flask, request, jsonify, render_template, Blueprint, flash, redirect, url_for
import json
import threading
import os
import logging
from datetime import datetime

# 导入项目模块
from core import StockMonitor
from models import db, User
from auth import auth, login_manager, admin_required

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化Flask应用
app = Flask(__name__)

# 配置应用
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/instance/users.db'  # 容器内绝对路径
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 会话超时时间：1小时

# 初始化数据库和登录管理器
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.session_protection = 'strong'

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
public_bp = Blueprint('public', __name__)

# 初始化库存监控器
monitor = StockMonitor()

# 避免模板变量冲突（与Vue冲突）
app.jinja_env.variable_start_string = '<<'
app.jinja_env.variable_end_string = '>>'

# 启动监控线程
def start_monitor_thread():
    """启动库存监控线程"""
    thread = threading.Thread(target=monitor.start_monitoring, daemon=True)
    thread.start()
    logger.info("库存监控线程已启动")

# 公共路由 - 仅展示库存信息
@public_bp.route('/')
def index():
    """公共首页，展示库存状态"""
    return render_template('public/index.html')

@public_bp.route('/api/public/stocks')
def public_stocks():
    """获取公共库存信息API"""
    try:
        stocks = monitor.config['stock']
        stock_list = []
        for name, details in stocks.items():
            stock_item = {
                "name": name,
                "url": details["url"],
                "status": details["status"],
                "last_changed": details.get("last_changed", "未知")
            }
            stock_list.append(stock_item)
        return jsonify(stock_list)
    except Exception as e:
        logger.error(f"获取公共库存信息失败: {str(e)}")
        return jsonify({"status": "error", "message": "获取库存信息失败"}), 500

# 管理员路由 - 需要登录
@admin_bp.route('/')
@admin_required
def index():
    """管理员首页"""
    return render_template('admin/index.html')

@admin_bp.route('/profile')
@admin_required
def profile():
    """管理员个人设置页面"""
    return render_template('admin/profile.html')

@admin_bp.route('/api/config', methods=['GET', 'POST'])
@admin_required
def config():
    """配置管理API"""
    try:
        if request.method == 'POST':
            data = request.json
            # 验证频率设置
            try:
                frequency = int(data.get('frequency', 30))
                if frequency < 10:  # 最小10秒，避免过于频繁
                    return jsonify({"status": "error", "message": "监控频率不能小于10秒"}), 400
                data['frequency'] = frequency
            except ValueError:
                return jsonify({"status": "error", "message": "监控频率必须是数字"}), 400
                
            # 更新配置
            monitor.config['config'] = data
            monitor.save_config()
            logger.info(f"用户 {current_user.username} 更新了系统配置")
            return jsonify({"status": "success", "message": "配置已更新"})
        else:
            # 返回当前配置
            return jsonify(monitor.config['config'])
    except Exception as e:
        logger.error(f"配置管理API出错: {str(e)}")
        return jsonify({"status": "error", "message": "操作失败"}), 500

@admin_bp.route('/api/stocks', methods=['GET', 'POST', 'DELETE'])
@admin_required
def stocks():
    """库存监控项管理API"""
    try:
        if request.method == 'POST':
            data = request.json
            stock_name = data.get('name')
            url = data.get('url')
            
            if not stock_name or not url:
                return jsonify({"status": "error", "message": "商品名称和URL不能为空"}), 400
                
            # 检查是否已存在
            if stock_name in monitor.config['stock']:
                return jsonify({"status": "error", "message": f"监控项 '{stock_name}' 已存在"}), 400
                
            # 添加新监控项
            monitor.config['stock'][stock_name] = {
                "url": url, 
                "status": False,
                "last_changed": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            monitor.save_config()
            logger.info(f"用户 {current_user.username} 添加了监控项: {stock_name}")
            return jsonify({"status": "success", "message": f"已添加监控项 '{stock_name}'", "name": stock_name})
            
        elif request.method == 'DELETE':
            stock_name = request.json.get('name')
            
            if not stock_name:
                return jsonify({"status": "error", "message": "请指定要删除的监控项"}), 400
                
            if stock_name in monitor.config['stock']:
                del monitor.config['stock'][stock_name]
                monitor.save_config()
                logger.info(f"用户 {current_user.username} 删除了监控项: {stock_name}")
                return jsonify({"status": "success", "message": f"已删除监控项 '{stock_name}'", "name": stock_name})
            return jsonify({"status": "error", "message": f"监控项 '{stock_name}' 不存在"}), 404
            
        else:  # GET
            stocks = monitor.config['stock']
            stock_list = []
            for name, details in stocks.items():
                stock_item = {
                    "name": name,
                    "url": details["url"],
                    "status": details["status"],
                    "last_changed": details.get("last_changed", "未知")
                }
                stock_list.append(stock_item)
            return jsonify(stock_list)
    except Exception as e:
        logger.error(f"库存监控项管理API出错: {str(e)}")
        return jsonify({"status": "error", "message": "操作失败"}), 500

@admin_bp.route('/api/reload', methods=['POST'])
@admin_required
def reload_config():
    """重新加载配置API"""
    try:
        monitor.reload()
        logger.info(f"用户 {current_user.username} 重新加载了配置")
        return jsonify({"status": "success", "message": "配置已重新加载"})
    except Exception as e:
        logger.error(f"重新加载配置API出错: {str(e)}")
        return jsonify({"status": "error", "message": "重新加载失败"}), 500

# 注册蓝图
app.register_blueprint(auth)
app.register_blueprint(admin_bp)
app.register_blueprint(public_bp)

# 初始化数据库和创建管理员用户
def init_database():
    """初始化数据库"""
    with app.app_context():
        # 确保instance目录存在且可写
        os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), exist_ok=True)
        
        db.create_all()
        
        # 检查是否已有管理员用户，没有则创建
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')  # 首次登录后应更改密码
            db.session.add(admin)
            db.session.commit()
            logger.warning("创建了默认管理员用户，请尽快登录并修改密码")

# 应用启动时初始化
init_database()
start_monitor_thread()

if __name__ == '__main__':
    # 生产环境应使用Gunicorn等WSGI服务器，此处仅为开发测试
    port = int(os.getenv('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
    