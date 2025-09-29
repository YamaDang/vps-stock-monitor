import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
import logging

# 创建admin蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 配置日志
logger = logging.getLogger(__name__)

# 检查是否为管理员的装饰器
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('您没有权限访问此页面', 'danger')
            logger.warning(f"Non-admin user {current_user.username} attempted to access admin area")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 监控目标管理页面
@admin_bp.route('/monitor_targets')
@login_required
@admin_required
def monitor_targets():
    from app import app, MonitorTarget
    with app.app_context():
        monitor_targets = MonitorTarget.query.all()
    return render_template('admin/monitor_targets.html', monitor_targets=monitor_targets)

# 添加监控目标页面
@admin_bp.route('/add_monitor_target', methods=['GET', 'POST'])
@login_required
@admin_required
def add_monitor_target():
    if request.method == 'POST':
        from app import app, db, MonitorTarget
        name = request.form['name']
        url = request.form['url']
        check_type = request.form['check_type']
        check_pattern = request.form['check_pattern']
        expected_result = request.form.get('expected_result', '')
        interval = int(request.form.get('interval', 300))
        use_flaresolverr = 'use_flaresolverr' in request.form
        
        # 创建新的监控目标
        new_target = MonitorTarget(
            name=name,
            url=url,
            check_type=check_type,
            check_pattern=check_pattern,
            expected_result=expected_result,
            interval=interval,
            is_active=True,
            use_flaresolverr=use_flaresolverr
        )
        
        try:
            with app.app_context():
                db.session.add(new_target)
                db.session.commit()
            logger.info(f"Admin {current_user.username} added new monitor target: {name}")
            flash('监控目标添加成功', 'success')
            return redirect(url_for('admin.monitor_targets'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding monitor target: {str(e)}")
            flash(f'添加监控目标失败: {str(e)}', 'danger')
            return redirect(url_for('admin.add_monitor_target'))
    
    return render_template('admin/add_monitor_target.html')

# 编辑监控目标
@admin_bp.route('/edit_monitor_target/<int:target_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_monitor_target(target_id):
    from datetime import datetime
    from app import app, db, MonitorTarget
    
    with app.app_context():
        target = MonitorTarget.query.get_or_404(target_id)
        
        if request.method == 'POST':
            try:
                target.name = request.form['name']
                target.url = request.form['url']
                target.check_type = request.form['check_type']
                target.check_pattern = request.form['check_pattern']
                target.expected_result = request.form.get('expected_result', '')
                target.interval = int(request.form.get('interval', 300))
                target.use_flaresolverr = 'use_flaresolverr' in request.form
                target.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"Admin {current_user.username} updated monitor target: {target.name}")
                flash('监控目标更新成功', 'success')
                return redirect(url_for('admin.monitor_targets'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating monitor target: {str(e)}")
                flash(f'更新监控目标失败: {str(e)}', 'danger')
                return redirect(url_for('admin.edit_monitor_target', target_id=target_id))
        
    return render_template('admin/edit_monitor_target.html', target=target)

# 删除监控目标
@admin_bp.route('/delete_monitor_target/<int:target_id>')
@login_required
@admin_required
def delete_monitor_target(target_id):
    from app import app, db, MonitorTarget, NotificationSetting, StatusCheck
    with app.app_context():
        target = MonitorTarget.query.get_or_404(target_id)
        
        # 先删除相关的通知设置和状态检查记录
        NotificationSetting.query.filter_by(monitor_target_id=target_id).delete()
        
        # 注意：在实际生产环境中，可能需要保留历史状态检查记录
        # 这里为了简化，我们也删除它们
        StatusCheck.query.filter_by(monitor_target_id=target_id).delete()
        
        # 删除监控目标
        db.session.delete(target)
        db.session.commit()
    
    logger.info(f"Admin {current_user.username} deleted monitor target: {target.name}")
    flash('监控目标删除成功', 'success')
    return redirect(url_for('admin.monitor_targets'))

# 切换监控目标状态
@admin_bp.route('/toggle_monitor_target/<int:target_id>')
@login_required
@admin_required
def toggle_monitor_target(target_id):
    from app import app, db, MonitorTarget
    with app.app_context():
        target = MonitorTarget.query.get_or_404(target_id)
        target.is_active = not target.is_active
        target.updated_at = datetime.utcnow()
        
        db.session.commit()
    
    status = "启用" if target.is_active else "禁用"
    logger.info(f"Admin {current_user.username} {status} monitor target: {target.name}")
    flash(f'监控目标已{status}', 'success')
    return redirect(url_for('admin.monitor_targets'))

# 通知设置管理页面
@admin_bp.route('/notification_settings')
@login_required
@admin_required
def notification_settings():
    from app import app, MonitorTarget, NotificationSetting
    # 获取所有监控目标和通知设置
    with app.app_context():
        monitor_targets = MonitorTarget.query.all()
        
        # 获取所有通知设置
        all_settings = []
        for target in monitor_targets:
            settings = NotificationSetting.query.filter_by(monitor_target_id=target.id).all()
            for setting in settings:
                setting.monitor_target_name = target.name
                all_settings.append(setting)
    
    return render_template('admin/notification_settings.html', 
                          notification_settings=all_settings, 
                          monitor_targets=monitor_targets)

# 添加通知设置
@admin_bp.route('/add_notification_setting', methods=['GET', 'POST'])
@login_required
@admin_required
def add_notification_setting():
    from app import app, MonitorTarget
    with app.app_context():
        monitor_targets = MonitorTarget.query.all()
    
    if request.method == 'POST':
            from app import app, db, NotificationSetting
            monitor_target_id = request.form['monitor_target_id']
            notification_type = request.form['notification_type']
            enabled = 'enabled' in request.form
            
            # 根据通知类型获取不同的设置
            settings = {}
            
            if notification_type == 'telegram':
                settings['token'] = request.form.get('telegram_token', '')
                settings['chat_id'] = request.form.get('telegram_chat_id', '')
            elif notification_type == 'xi_zhi':
                settings['token'] = request.form.get('xi_zhi_token', '')
            elif notification_type == 'webhook':
                settings['url'] = request.form.get('webhook_url', '')
            
            # 创建新的通知设置，关联到当前管理员用户
            new_setting = NotificationSetting(
                monitor_target_id=monitor_target_id if monitor_target_id else None,
                user_id=current_user.id,
                notification_type=notification_type,
                settings=settings,
                enabled=enabled
            )
        
            with app.app_context():
                db.session.add(new_setting)
                db.session.commit()
            
            with app.app_context():
                if monitor_target_id:
                    target = MonitorTarget.query.get(monitor_target_id)
                    logger.info(f"Admin {current_user.username} added notification setting for {target.name}")
                else:
                    logger.info(f"Admin {current_user.username} added global notification setting")
            flash('通知设置添加成功', 'success')
            return redirect(url_for('admin.notification_settings'))
        
    return render_template('admin/add_notification_setting.html', 
                          monitor_targets=monitor_targets)

# 编辑通知设置
@admin_bp.route('/edit_notification_setting/<int:setting_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_notification_setting(setting_id):
    from app import app, NotificationSetting, MonitorTarget
    with app.app_context():
        setting = NotificationSetting.query.get_or_404(setting_id)
        monitor_targets = MonitorTarget.query.all()
    
    if request.method == 'POST':
        from app import app, db
        # 更新设置
        settings = {}
        
        if request.form['notification_type'] == 'telegram':
            settings['token'] = request.form.get('telegram_token', '')
            settings['chat_id'] = request.form.get('telegram_chat_id', '')
        elif request.form['notification_type'] == 'xi_zhi':
            settings['token'] = request.form.get('xi_zhi_token', '')
        elif request.form['notification_type'] == 'webhook':
            settings['url'] = request.form.get('webhook_url', '')
        
        with app.app_context():
            setting = NotificationSetting.query.get_or_404(setting_id)
            setting.monitor_target_id = request.form['monitor_target_id'] if request.form['monitor_target_id'] else None
            setting.notification_type = request.form['notification_type']
            setting.enabled = 'enabled' in request.form
            setting.settings = settings
            
            db.session.commit()
            
            # 处理日志记录，考虑到可能没有特定监控目标
            if setting.monitor_target_id:
                target = MonitorTarget.query.get(setting.monitor_target_id)
                logger.info(f"Admin {current_user.username} updated notification setting for {target.name}")
            else:
                logger.info(f"Admin {current_user.username} updated global notification setting")
        flash('通知设置更新成功', 'success')
        return redirect(url_for('admin.notification_settings'))
        
    return render_template('admin/edit_notification_setting.html', 
                          setting=setting, 
                          monitor_targets=monitor_targets)

# 删除通知设置
@admin_bp.route('/delete_notification_setting/<int:setting_id>')
@login_required
@admin_required
def delete_notification_setting(setting_id):
    from app import app, db, NotificationSetting, MonitorTarget
    with app.app_context():
        setting = NotificationSetting.query.get_or_404(setting_id)
        
        db.session.delete(setting)
        db.session.commit()
        
        # 处理日志记录，考虑到可能没有特定监控目标
        if setting.monitor_target_id:
            target = MonitorTarget.query.get(setting.monitor_target_id)
            logger.info(f"Admin {current_user.username} deleted notification setting for {target.name}")
        else:
            logger.info(f"Admin {current_user.username} deleted global notification setting")
    flash('通知设置删除成功', 'success')
    return redirect(url_for('admin.notification_settings'))

# 执行立即检查
@admin_bp.route('/check_now/<int:target_id>')
@login_required
@admin_required
def check_now(target_id):
    from app import app, MonitorTarget, db, StatusCheck
    from monitor import check_stock_status, send_notification, NotificationSetting
    import time
    
    try:
        with app.app_context():
            # 获取目标并确保它在当前会话中
            target = MonitorTarget.query.get_or_404(target_id)
            
            logger.info(f"Admin {current_user.username} manually checking {target.name}")
            
            try:
                # 只检查指定的目标，而不是所有目标
                is_available, message, response_time = check_stock_status(target)
                
                # 创建状态检查记录
                status_check = StatusCheck(
                    monitor_target_id=target.id,
                    is_available=is_available,
                    response_time=response_time,
                    message=message
                )
                db.session.add(status_check)
                
                # 检查是否需要发送通知（状态变化时）
                notification_settings = NotificationSetting.query.filter_by(
                    monitor_target_id=target.id,
                    enabled=True
                ).all()
                
                if notification_settings:
                    # 获取上一次的状态检查结果
                    previous_check = StatusCheck.query.filter_by(
                        monitor_target_id=target.id
                    ).order_by(StatusCheck.timestamp.desc()).offset(1).first()
                    
                    # 如果是第一次检查或者状态发生变化，则发送通知
                    if not previous_check or previous_check.is_available != is_available:
                        logger.info(f"Status changed for {target.name}, sending notifications")
                        for notification_setting in notification_settings:
                            # 确保在同一个会话中使用这些对象
                            notification_setting = db.session.merge(notification_setting)
                            send_notification(notification_setting, target, status_check)
                
                db.session.commit()
                
                logger.info(f"Admin {current_user.username} manually checked {target.name}")
                flash('已立即执行检查', 'success')
                
            except Exception as check_error:
                # 发生错误时回滚会话
                db.session.rollback()
                logger.error(f"Check error for {target.name}: {str(check_error)}")
                flash(f'检查过程中出错: {str(check_error)}', 'danger')
                
    except Exception as e:
        logger.error(f"Error manually checking target {target_id}: {str(e)}")
        flash(f'检查执行失败: {str(e)}', 'danger')
    
    # 重定向回来源页面，如果没有来源页面则回退到dashboard
    referrer = request.headers.get('Referer')
    if referrer and '/statistics' in referrer:
        return redirect(url_for('admin.statistics'))
    return redirect(url_for('dashboard'))

# 监控日志页面
@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    # 从请求参数中获取limit，如果没有则使用默认值500
    limit = request.args.get('limit', 500, type=int)
    import re
    from datetime import datetime
    
    try:
        with open('logs/app.log', 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
        
        # 反转日志，显示最新的在前
        log_lines.reverse()
        # 限制显示的日志行数，最多500行
        log_lines = log_lines[:min(limit, 500)]  
        
        # 解析日志行并创建结构化的日志对象
        log_items = []
        log_pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (.*?) - (\w+) - (.*)$'
        
        for line in log_lines:
            line = line.strip()
            if not line:  # 跳过空行
                continue
                
            match = re.match(log_pattern, line)
            if match:
                # 结构化日志行
                timestamp_str, source, level, message = match.groups()
                try:
                    # 解析时间戳
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                except ValueError:
                    timestamp = datetime.now()
                
                log_items.append({
                    'timestamp': timestamp,
                    'source': source,
                    'level': level.lower(),
                    'message': message
                })
            else:
                # 非结构化日志行
                log_items.append({
                    'timestamp': datetime.now(),
                    'source': 'system',
                    'level': 'info',
                    'message': line
                })
                
    except Exception as e:
        log_items = [{
            'timestamp': datetime.now(),
            'source': 'error',
            'level': 'error',
            'message': f"无法读取日志文件: {str(e)}"
        }]
    
    return render_template('admin/logs.html', logs={'items': log_items}, limit=limit)

# 数据统计页面
@admin_bp.route('/statistics')
@login_required
@admin_required
def statistics():
    from datetime import datetime, timedelta
    from app import app, MonitorTarget, NotificationSetting, StatusCheck
    
    # 初始化变量
    total_monitors = 0
    online_monitors = 0
    total_notifications = 0
    avg_response_time = 0
    monitor_targets = []
    
    with app.app_context():
        # 获取监控目标数量
        total_monitors = MonitorTarget.query.count()
        online_monitors = MonitorTarget.query.filter_by(is_active=True).count()
        
        # 获取通知设置数量
        total_notifications = NotificationSetting.query.count()
        
        # 获取平均响应时间（如果有数据的话）
        recent_checks = StatusCheck.query.order_by(StatusCheck.timestamp.desc()).limit(100).all()
        if recent_checks:
            avg_response_time = sum(check.response_time for check in recent_checks if check.response_time) / len([check for check in recent_checks if check.response_time])
        
        # 获取监控目标列表
        monitor_targets = MonitorTarget.query.all()
    
    # 构建库存状态分布数据
    stock_status_data = {
        'available': 3,  # 示例数据
        'unavailable': 2,  # 示例数据
        'unknown': 0  # 示例数据
    }
    
    # 构建时间标签（过去24小时，每2小时一个点）
    time_labels = []
    now = datetime.utcnow()
    for i in range(12):
        time_label = (now - timedelta(hours=i*2)).strftime('%H:%M')
        time_labels.insert(0, time_label)  # 插入到开头以保持时间顺序
    
    # 构建监控目标统计详情（添加示例数据）
    monitor_stats = []
    
    # 如果没有监控目标，添加一些示例数据用于展示
    if not monitor_targets:
        # 创建示例监控目标数据
        sample_colors = ['#28a745', '#007bff', '#dc3545', '#ffc107', '#17a2b8']
        
        for i in range(3):
            # 生成随机响应时间数据
            response_times = [round(100 + (i+1)*50 + j*10) for j in range(12)]
            
            monitor_stats.append({
                'name': f'示例VPS {i+1}',
                'url': f'https://example.com/vps{i+1}',
                'status': 'available' if i % 2 == 0 else 'unavailable',
                'latest_response_time': response_times[-1],
                'last_checked': now.strftime('%Y-%m-%d %H:%M:%S'),
                'success_rate': 95 + i*2,
                'response_times': response_times,
                'color': sample_colors[i]
            })
    else:
        # 真实数据处理
        sample_colors = ['#28a745', '#007bff', '#dc3545', '#ffc107', '#17a2b8']
        for i, target in enumerate(monitor_targets):
            with app.app_context():
                # 获取最新状态
                latest_status = StatusCheck.query.filter_by(monitor_target_id=target.id).order_by(StatusCheck.timestamp.desc()).first()
            
            # 获取历史响应时间（示例数据）
            response_times = [round(100 + (i+1)*50 + j*10) for j in range(12)]
            
            # 计算成功率（示例数据）
            success_rate = 95 + i*2 if i < 4 else 95
            
            monitor_stats.append({
                'name': target.name,
                'url': target.url,
                'status': 'available' if latest_status and latest_status.is_available else 'unavailable',
                'latest_response_time': latest_status.response_time if latest_status and latest_status.response_time else 0,
                'last_checked': latest_status.timestamp.strftime('%Y-%m-%d %H:%M:%S') if latest_status else '从未检查',
                'success_rate': success_rate,
                'response_times': response_times,
                'color': sample_colors[i % len(sample_colors)]
            })
            
            # 更新库存状态分布
            if latest_status:
                if latest_status.is_available:
                    stock_status_data['available'] += 1
                else:
                    stock_status_data['unavailable'] += 1
            else:
                stock_status_data['unknown'] += 1
    
    return render_template('admin/statistics.html', 
                          total_monitors=total_monitors,
                          online_monitors=online_monitors,
                          total_notifications=total_notifications,
                          avg_response_time=avg_response_time,
                          stock_status_data=stock_status_data,
                          monitor_stats=monitor_stats,
                          time_labels=time_labels)


# 注册蓝图到app
def register_blueprint(app):
    app.register_blueprint(admin_bp)