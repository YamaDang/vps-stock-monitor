from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User
from datetime import datetime

auth = Blueprint('auth', __name__)
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    # 对于API请求，返回JSON错误
    if request.path.startswith('/api/'):
        return jsonify({"status": "error", "message": "需要管理员权限"}), 401
    # 对于页面请求，重定向到登录页
    return redirect(url_for('auth.login', next=request.url))

@auth.route('/login', methods=['GET', 'POST'])
def login():
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
            if request.is_json:
                return jsonify({"status": "error", "message": "用户名或密码不正确"}), 401
            flash('用户名或密码不正确')
            return redirect(url_for('auth.login'))
            
        login_user(user)
        user.update_last_login()
        
        next_page = request.args.get('next')
        if request.is_json:
            return jsonify({"status": "success", "message": "登录成功", "redirect": next_page or url_for('admin.index')})
        return redirect(next_page or url_for('admin.index'))
        
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功退出登录')
    return redirect(url_for('public.index'))

@auth.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({"status": "error", "message": "请输入旧密码和新密码"}), 400
        
    if not current_user.check_password(old_password):
        return jsonify({"status": "error", "message": "旧密码不正确"}), 400
        
    if len(new_password) < 6:
        return jsonify({"status": "error", "message": "新密码长度至少为6位"}), 400
        
    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({"status": "success", "message": "密码已成功修改，请重新登录"})

# 管理员权限装饰器
def admin_required(f):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return unauthorized()
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper
    