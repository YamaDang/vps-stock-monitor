import os
import logging
import sqlite3
from flask import Flask, jsonify, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy

# 配置日志
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/app.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()
logger.info("Starting simplified app")

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'

# 使用绝对路径的数据库URL，确保在Docker容器中正确配置
DATABASE_PATH = '/app/instance/database.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

logger.info(f"Using database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
logger.info(f"Current working directory: {os.getcwd()}")

# 确保数据库目录存在
instance_dir = '/app/instance'
if not os.path.exists(instance_dir):
    try:
        os.makedirs(instance_dir)
        logger.info(f"Created instance directory: {instance_dir}")
    except Exception as e:
        logger.error(f"Failed to create instance directory: {str(e)}")

# 检查目录权限
if os.path.exists(instance_dir):
    logger.info(f"Instance directory permissions: {oct(os.stat(instance_dir).st_mode)[-3:]}")
    logger.info(f"Instance directory owner: {os.stat(instance_dir).st_uid}:{os.stat(instance_dir).st_gid}")

# 尝试直接使用sqlite3连接，绕过SQLAlchemy，用于诊断
logger.info("Attempting direct SQLite connection test...")
try:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    conn.close()
    logger.info(f"Direct SQLite connection successful: {result}")
except Exception as e:
    logger.error(f"Direct SQLite connection failed: {str(e)}")

# 初始化数据库
db = SQLAlchemy(app)

from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# 加载环境变量
load_dotenv()

# 数据库模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notification_settings = db.relationship('NotificationSetting', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class MonitorTarget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    check_type = db.Column(db.String(20), default='text')  # text, selector, api
    check_pattern = db.Column(db.String(500))  # 文本模式、CSS选择器或API路径
    expected_result = db.Column(db.String(500))  # 期望结果
    interval = db.Column(db.Integer, default=300)  # 监控间隔(秒)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    use_flaresolverr = db.Column(db.Boolean, default=False)
    status_checks = db.relationship('StatusCheck', backref='monitor_target', lazy=True)
    notification_settings = db.relationship('NotificationSetting', backref='monitor_target', lazy=True)

class StatusCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monitor_target_id = db.Column(db.Integer, db.ForeignKey('monitor_target.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_available = db.Column(db.Boolean, default=False)
    response_time = db.Column(db.Float)  # 响应时间(毫秒)
    message = db.Column(db.Text)  # 状态消息或错误信息

class NotificationSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monitor_target_id = db.Column(db.Integer, db.ForeignKey('monitor_target.id'), nullable=True)  # 设为可为空，支持任意监控目标
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(20), nullable=False)  # telegram, xi_zhi, webhook
    settings = db.Column(db.JSON)  # 存储通知配置(如API密钥、聊天ID等)
    enabled = db.Column(db.Boolean, default=True)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 登录管理器回调
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 上下文处理器 - 为模板提供工具函数
@app.context_processor
def utility_processor():
    def convert_to_beijing_time(utc_time):
        # 将UTC时间转换为北京时间(UTC+8)
        beijing_time = utc_time + timedelta(hours=8)
        return beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    
    return dict(convert_to_beijing_time=convert_to_beijing_time)

# 简单的数据模型，保留用于测试
class TestModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(50))

# 初始化数据库表
def init_db():
    try:
        with app.app_context():
            logger.info("Initializing database...")
            db.create_all()
            logger.info("Database tables created")
            
            # 创建管理员用户（如果不存在）
            if User.query.count() == 0:
                admin_username = os.getenv('ADMIN_USERNAME', 'admin')
                admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')  # 默认密码，建议在生产环境中通过环境变量设置
                admin = User(username=admin_username, is_admin=True)
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                logger.info(f"Created admin user: {admin_username}")
            
            # 添加测试数据
            if TestModel.query.count() == 0:
                test1 = TestModel(data="Test record 1")
                test2 = TestModel(data="Test record 2")
                db.session.add(test1)
                db.session.add(test2)
                db.session.commit()
                logger.info("Added test records")
            
            # 查询测试数据
            count = TestModel.query.count()
            logger.info(f"Found {count} test record(s)")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

from sqlalchemy import text

# 添加一个简单的路由用于测试
@app.route('/test_db')
def test_db_connection():
    try:
        with app.app_context():
            # 尝试简单的查询来验证数据库连接
            db.session.execute(text('SELECT 1'))
            count = TestModel.query.count()
            return jsonify({
                'status': 'success',
                'message': 'Database connection successful',
                'record_count': count
            })
    except Exception as e:
        logger.error(f"Test route failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            logger.info(f"User {username} logged in successfully")
            return redirect(url_for('dashboard'))
        
        flash('用户名或密码错误', 'danger')
        logger.warning(f"Failed login attempt for username: {username}")
        
    return render_template('login.html')

# 登出页面
@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    logger.info(f"User {username} logged out")
    return redirect(url_for('login'))

# 仪表盘页面
@app.route('/')
def dashboard():
    monitor_targets = MonitorTarget.query.all()
    
    # 对每个监控目标，获取最新的状态检查结果
    for target in monitor_targets:
        latest_status = StatusCheck.query.filter_by(monitor_target_id=target.id).order_by(StatusCheck.timestamp.desc()).first()
        target.latest_status = latest_status
    
    # 公共页面，非管理员访问
    is_admin = False
    # 如果用户已登录，检查是否为管理员
    if current_user.is_authenticated:
        is_admin = current_user.is_admin
        
    return render_template('dashboard.html', monitor_targets=monitor_targets, is_admin=is_admin)

# 修改密码页面
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if not current_user.check_password(current_password):
            flash('当前密码错误', 'danger')
            return redirect(url_for('change_password'))
        
        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'danger')
            return redirect(url_for('change_password'))
        
        current_user.set_password(new_password)
        db.session.commit()
        logger.info(f"User {current_user.username} changed password successfully")
        flash('密码修改成功', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('change_password.html')

# 配置定时任务
# 使用BackgroundScheduler并设置为在后台线程运行
scheduler = BackgroundScheduler(job_defaults={'coalesce': True, 'max_instances': 1})

def init_scheduler():
    try:
        # 使用延迟导入来避免循环导入问题
        def monitor_stock_status_wrapper():
            try:
                from monitor import monitor_stock_status
                logger.info("Executing scheduled stock monitoring...")
                monitor_stock_status()
                logger.info("Scheduled stock monitoring completed")
            except ImportError:
                logger.warning("Monitor module not found, skipping stock monitoring")
            except Exception as e:
                logger.error(f"Error in stock monitoring: {str(e)}")
        
        # 添加定时任务，每300秒执行一次库存检查
        scheduler.add_job(
            func=monitor_stock_status_wrapper,
            trigger=IntervalTrigger(seconds=300),
            id='stock_monitoring_job',
            name='Periodic stock monitoring',
            replace_existing=True,
            misfire_grace_time=60  # 允许任务错过后60秒内执行
        )
        
        # 启动调度器
        scheduler.start()
        logger.info("Scheduler initialized and started successfully")
        # 添加额外的日志记录，确认调度器状态
        logger.info(f"Scheduler running: {scheduler.running}")
        logger.info(f"Scheduled jobs: {len(scheduler.get_jobs())}")
        # 立即执行一次检查，确保功能正常
        monitor_stock_status_wrapper()
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {str(e)}")

# 应用启动时的初始化
def init_app():
    init_db()
    
    try:
        init_scheduler()  # 启动定时任务
    except Exception:
        logger.warning("Failed to initialize scheduler, continuing without it")
    
    try:
        from admin import register_blueprint as register_admin_blueprint
        register_admin_blueprint(app)
        logger.info("Admin blueprint registered")
    except ImportError:
        logger.warning("Admin module not found, skipping admin blueprint registration")
    except Exception as e:
        logger.error(f"Failed to register admin blueprint: {str(e)}")
    
    # 添加上下文处理器，使now变量在所有模板中可用
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # 添加时间格式化过滤器，将UTC时间转换为北京时间
    @app.template_filter('datetimeformat')
    def datetimeformat(value):
        from datetime import datetime, timedelta
        if isinstance(value, str):
            # 如果值是字符串，尝试解析为datetime对象
            try:
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return value
        elif isinstance(value, datetime):
            dt = value
        else:
            return value
        
        # 转换为北京时间（UTC+8）
        cst_time = dt + timedelta(hours=8)
        # 返回格式化后的时间字符串
        return cst_time.strftime('%Y-%m-%d %H:%M:%S')

# 当作为WSGI应用导入时，延迟初始化以确保应用上下文正确设置
def wsgi_app(environ, start_response):
    # 这是WSGI应用的入口点
    return app.wsgi_app(environ, start_response)

# 为gunicorn等WSGI服务器提供一个明确的应用对象
def create_app():
    """创建并初始化Flask应用"""
    logger.info("Creating app...")
    
    # 应用已经在上面创建，这里只需要初始化
    with app.app_context():
        init_app()
        
    logger.info("App created successfully")
    return app

# 为gunicorn提供一个默认的应用对象
application = create_app()

# 直接运行时使用
if __name__ == '__main__':
    init_app()
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except (KeyboardInterrupt, SystemExit):
        # 优雅关闭调度器
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler shut down gracefully")