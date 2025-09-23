from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User
from datetime import datetime
import logging

# 配置日志
logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    """加载用户回调函数"""
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """未授权访问处理"""
    if request.path.startswith('/api/'):
        return jsonify({"status": "error", "message": "请先登录"}), 401
    return redirect(url_for('auth.login', next=request.url))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """登录处理"""
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
        
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            logger.warning(f"登录失败，用户名或密码不正确: {username}")
            if request.is_json:
                return jsonify({"status": "error", "message": "用户名或密码不正确"}), 401
            flash('用户名或密码不正确')
            return redirect(url_for('auth.login'))
            
        # 登录用户
        login_user(user, remember=True)
        user.update_last_login()
        db.session.commit()
        
        logger.info(f"用户登录成功: {username}")
        
        # 处理跳转
        next_page = request.args.get('next')
        if request.is_json:
            return jsonify({
                "status": "success", 
                "message": "登录成功",
                "redirect": next_page or url_for('admin.index')
            })
        return redirect(next_page or url_for('admin.index'))
        
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    """登出处理"""
    logger.info(f"用户登出: {current_user.username}")
    logout_user()
    flash('您已成功登出')
    return redirect(url_for('public.index'))

@auth.route('/api/admin/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码API"""
    data = request.get_json()
    current_pwd = data.get('current_password')
    new_pwd = data.get('new_password')
    confirm_pwd = data.get('confirm_password')
    
    # 验证输入
    if not all([current_pwd, new_pwd, confirm_pwd]):
        return jsonify({"status": "error", "message": "请填写所有字段"}), 400
        
    if new_pwd != confirm_pwd:
        return jsonify({"status": "error", "message": "两次输入的新密码不一致"}), 400
        
    if len(new_pwd) < 6:
        return jsonify({"status": "error", "message": "新密码长度至少为6位"}), 400
        
    # 验证当前密码
    if not current_user.check_password(current_pwd):
        return jsonify({"status": "error", "message": "当前密码不正确"}), 400
        
    # 更新密码
    current_user.set_password(new_pwd)
    db.session.commit()
    logger.info(f"用户 {current_user.username} 修改了密码")
    
    return jsonify({"status": "success", "message": "密码修改成功，请重新登录"})

# 管理员权限装饰器
def admin_required(f):
    """管理员权限装饰器"""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        # 目前只有admin用户，未来可扩展角色系统
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper
    