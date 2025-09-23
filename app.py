import os
import os
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///data/database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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
    monitor_target_id = db.Column(db.Integer, db.ForeignKey('monitor_target.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(20), nullable=False)  # telegram, xi_zhi, webhook
    settings = db.Column(db.JSON)  # 存储通知配置(如API密钥、聊天ID等)
    enabled = db.Column(db.Boolean, default=True)

# 登录管理器回调
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 初始化数据库和创建管理员用户
def init_db():
    with app.app_context():
        db.create_all()
        
        # 检查是否存在管理员用户
        admin = User.query.filter_by(username=os.environ.get('ADMIN_USERNAME', 'admin')).first()
        if not admin:
            admin = User(username=os.environ.get('ADMIN_USERNAME', 'admin'), is_admin=True)
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
            db.session.add(admin)
            db.session.commit()
            logger.info(f"Created admin user: {admin.username}")

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
scheduler = BackgroundScheduler()

def init_scheduler():
    # 暂时禁用定时任务以解决导入问题
    logger.info("Scheduler initialization skipped for preview")

# 应用启动时的初始化
def init_app():
    init_db()
    # init_scheduler()  # 暂时禁用定时任务
    from admin import register_blueprint as register_admin_blueprint
    register_admin_blueprint(app)
    
    # 添加上下文处理器，使now变量在所有模板中可用
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

# 在应用上下文之外调用初始化函数
if __name__ == '__main__':
    init_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # 在生产环境中使用gunicorn等WSGI服务器时初始化
    init_app()