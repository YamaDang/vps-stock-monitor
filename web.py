from flask import Flask, request, jsonify, render_template, Blueprint, flash, redirect, url_for
from core import StockMonitor
import json
import threading
import os
from models import db, User
from auth import auth, login_manager, admin_required
from flask_login import login_required, current_user

# 初始化Flask应用
app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')  # 生产环境需更换为随机密钥
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 会话超时时间，1小时

# 初始化数据库和登录管理器
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问该页面'

# 注册认证蓝图
app.register_blueprint(auth)

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
public_bp = Blueprint('public', __name__)

# 初始化库存监控器
monitor = StockMonitor()

# 避免模板变量冲突（与Vue冲突）
app.jinja_env.variable_start_string = '<<'
app.jinja_env.variable_end_string = '>>'

# 公共路由 - 仅展示库存信息
@public_bp.route('/')
def index():
    return render_template('public/index.html')

@public_bp.route('/api/public/stocks')
def public_stocks():
    """获取公共可见的库存信息"""
    with monitor.lock:
        stocks = monitor.config['stock'].copy()
    
    stock_list = []
    for name, details in stocks.items():
        stock_item = {
            "name": name,
            "url": details["url"],
            "status": details["status"]
        }
        stock_list.append(stock_item)
    return jsonify(stock_list)

# 管理员路由 - 需要登录
@admin_bp.route('/')
@admin_required
def index():
    return render_template('admin/index.html')

@admin_bp.route('/profile')
@admin_required
def profile():
    return render_template('admin/profile.html')

@admin_bp.route('/api/config', methods=['GET', 'POST'])
@admin_required
def config():
    """获取或更新系统配置"""
    if request.method == 'POST':
        try:
            data = request.json
            # 验证配置数据
            if 'frequency' in data:
                try:
                    # 确保监控频率是合理的数值（10-3600秒）
                    frequency = int(data['frequency'])
                    data['frequency'] = max(10, min(3600, frequency))
                except ValueError:
                    return jsonify({"status": "error", "message": "监控频率必须是数字"}), 400
            
            with monitor.lock:
                monitor.config['config'].update(data)
            monitor.save_config()
            return jsonify({"status": "success", "message": "配置已更新"})
        except Exception as e:
            return jsonify({"status": "error", "message": f"更新配置失败: {str(e)}"}), 500
    else:
        with monitor.lock:
            config_data = monitor.config['config'].copy()
        return jsonify(config_data)

@admin_bp.route('/api/stocks', methods=['GET', 'POST', 'DELETE'])
@admin_required
def stocks():
    """管理监控项"""
    if request.method == 'POST':
        try:
            data = request.json
            if not data.get('name') or not data.get('url'):
                return jsonify({"status": "error", "message": "商品名称和URL不能为空"}), 400
                
            stock_name = data['name'].strip()
            url = data['url'].strip()
            
            with monitor.lock:
                if stock_name in monitor.config['stock']:
                    return jsonify({"status": "error", "message": f"监控项 '{stock_name}' 已存在"}), 400
                    
                monitor.config['stock'][stock_name] = {
                    "url": url, 
                    "status": False
                }
            monitor.save_config()
            return jsonify({
                "status": "success", 
                "message": f"已添加监控项 '{stock_name}'",
                "stock": {
                    "name": stock_name,
                    "url": url,
                    "status": False
                }
            })
        except Exception as e:
            return jsonify({"status": "error", "message": f"添加监控项失败: {str(e)}"}), 500
            
    elif request.method == 'DELETE':
        try:
            data = request.json
            if not data.get('name'):
                return jsonify({"status": "error", "message": "商品名称不能为空"}), 400
                
            stock_name = data['name'].strip()
            with monitor.lock:
                if stock_name not in monitor.config['stock']:
                    return jsonify({"status": "error", "message": f"监控项 '{stock_name}' 不存在"}), 404
                    
                del monitor.config['stock'][stock_name]
            monitor.save_config()
            return jsonify({"status": "success", "message": f"已删除监控项 '{stock_name}'", "name": stock_name})
        except Exception as e:
            return jsonify({"status": "error", "message": f"删除监控项失败: {str(e)}"}), 500
            
    else:
        with monitor.lock:
            stocks = monitor.config['stock'].copy()
            
        stock_list = []
        for name, details in stocks.items():
            stock_item = {
                "name": name,
                "url": details["url"],
                "status": details["status"]
            }
            stock_list.append(stock_item)
        return jsonify(stock_list)

@admin_bp.route('/api/reload', methods=['POST'])
@admin_required
def reload_config():
    """重新加载配置"""
    try:
        monitor.reload()
        return jsonify({"status": "success", "message": "配置已重新加载"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"重新加载配置失败: {str(e)}"}), 500

# 注册蓝图
app.register_blueprint(admin_bp)
app.register_blueprint(public_bp)

# 初始化数据库和创建管理员用户
def init_db():
    with app.app_context():
        db.create_all()
        # 检查是否已有管理员用户，没有则创建
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')  # 首次登录后应更改密码
            db.session.add(admin)
            db.session.commit()
            print("已创建默认管理员用户: admin (密码: admin123)")
        else:
            print("管理员用户已存在")

# 启动监控线程
def start_monitor_thread():
    thread = threading.Thread(target=monitor.start_monitoring)
    thread.daemon = True
    thread.start()
    print("监控线程已启动")

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    # 启动监控线程
    start_monitor_thread()
    # 启动Web服务
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host=host, port=port)
    