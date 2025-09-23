from flask import Flask, request, jsonify, render_template, Blueprint
from core import StockMonitor
import threading
from models import db, User
from auth import auth, login_manager, admin_required
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库和登录管理器
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# 注册蓝图
app.register_blueprint(auth)

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
public_bp = Blueprint('public', __name__)

# 初始化监控器
monitor = StockMonitor()

# 避免模板变量冲突
app.jinja_env.variable_start_string = '<<'
app.jinja_env.variable_end_string = '>>'

# 公共路由 - 仅展示库存信息
@public_bp.route('/')
def index():
    return render_template('public/index.html')

@public_bp.route('/api/public/stocks')
def public_stocks():
    with monitor.lock:
        stocks = monitor.config['stock']
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

@admin_bp.route('/api/config', methods=['GET', 'POST'])
@admin_required
def config():
    if request.method == 'POST':
        data = request.json
        with monitor.lock:
            monitor.config['config'] = data
            monitor.save_config()
        return jsonify({"status": "success", "message": "配置已更新"})
    else:
        with monitor.lock:
            return jsonify(monitor.config['config'])

@admin_bp.route('/api/stocks', methods=['GET', 'POST', 'DELETE'])
@admin_required
def stocks():
    if request.method == 'POST':
        data = request.json
        stock_name = data['name']
        url = data['url']
        
        with monitor.lock:
            if stock_name in monitor.config['stock']:
                return jsonify({"status": "error", "message": f"监控项 '{stock_name}' 已存在"}), 400
                
            monitor.config['stock'][stock_name] = {"url": url, "status": False}
            monitor.save_config()
        return jsonify({"status": "success", "message": f"已添加监控项 '{stock_name}'"}), 201
        
    elif request.method == 'DELETE':
        stock_name = request.json['name']
        with monitor.lock:
            if stock_name in monitor.config['stock']:
                del monitor.config['stock'][stock_name]
                monitor.save_config()
                return jsonify({"status": "success", "message": f"已删除监控项 '{stock_name}'"}), 200
            return jsonify({"status": "error", "message": f"监控项 '{stock_name}' 不存在"}), 404
            
    else:
        with monitor.lock:
            stocks = monitor.config['stock']
            stock_list = []
            for name, details in stocks.items():
                stock_item = {
                    "name": name,
                    "url": details["url"],
                    "status": details["status"]
                }
                stock_list.append(stock_item)
        return jsonify(stock_list)

# 注册蓝图
app.register_blueprint(admin_bp)
app.register_blueprint(public_bp)

# 初始化数据库
def init_db():
    with app.app_context():
        db.create_all()
        # 检查是否已有管理员用户
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')  # 首次登录后应立即更改
            db.session.add(admin)
            db.session.commit()

# 启动监控线程
def start_monitor():
    thread = threading.Thread(target=monitor.start_monitoring)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    init_db()
    start_monitor()
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
