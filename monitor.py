import logging
import logging
import os
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
from app import app, db, MonitorTarget, StatusCheck, NotificationSetting

# 配置日志
logger = logging.getLogger(__name__)

# 获取FlareSolverr URL
FLARESOLVERR_URL = os.environ.get('FLARESOLVERR_URL', 'http://flaresolverr:8191/v1')

# 使用FlareSolverr获取页面内容
def get_page_with_flaresolverr(url):
    try:
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000
        }
        response = requests.post(FLARESOLVERR_URL, json=payload)
        data = response.json()
        
        if data.get("status") == "ok":
            logger.info(f"Successfully fetched {url} using FlareSolverr")
            return data["solution"]["response"]
        else:
            logger.error(f"Failed to fetch {url} with FlareSolverr: {data.get('message')}")
            return None
    except Exception as e:
        logger.error(f"Error using FlareSolverr for {url}: {str(e)}")
        return None

# 直接使用requests获取页面内容
def get_page_direct(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully fetched {url} directly")
        return response.text
    except Exception as e:
        logger.error(f"Error fetching {url} directly: {str(e)}")
        return None

# 根据监控目标类型检查库存状态
def check_stock_status(monitor_target):
    start_time = time.time()
    is_available = False
    message = ""
    
    try:
        # 获取页面内容
        if monitor_target.use_flaresolverr:
            content = get_page_with_flaresolverr(monitor_target.url)
        else:
            content = get_page_direct(monitor_target.url)
        
        if not content:
            message = "无法获取页面内容"
            return is_available, message
        
        # 根据检查类型判断库存状态
        if monitor_target.check_type == 'text':
            # 文本匹配检查
            if monitor_target.check_pattern in content:
                is_available = True
                message = f"找到匹配文本: {monitor_target.check_pattern}"
            else:
                message = f"未找到匹配文本: {monitor_target.check_pattern}"
        
        elif monitor_target.check_type == 'selector':
            # CSS选择器检查
            soup = BeautifulSoup(content, 'html.parser')
            elements = soup.select(monitor_target.check_pattern)
            
            if elements:
                element_text = ' '.join([elem.get_text().strip() for elem in elements])
                
                if monitor_target.expected_result:
                    if monitor_target.expected_result in element_text:
                        is_available = True
                        message = f"选择器元素包含期望结果: {monitor_target.expected_result}"
                    else:
                        message = f"选择器元素不包含期望结果"
                else:
                    is_available = True
                    message = f"找到选择器元素: {monitor_target.check_pattern}"
            else:
                message = f"未找到选择器元素: {monitor_target.check_pattern}"
        
        elif monitor_target.check_type == 'api':
            # API响应检查
            try:
                response_json = requests.get(monitor_target.url).json()
                
                # 简单的路径解析，如 'data.stock.available'
                if monitor_target.check_pattern:
                    value = response_json
                    for part in monitor_target.check_pattern.split('.'):
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            value = None
                            break
                    
                    if value is not None:
                        if monitor_target.expected_result:
                            if str(value) == monitor_target.expected_result:
                                is_available = True
                                message = f"API响应符合期望结果"
                            else:
                                message = f"API响应不符合期望结果"
                        else:
                            is_available = True
                            message = f"API响应包含路径: {monitor_target.check_pattern}"
                    else:
                        message = f"API响应中未找到路径: {monitor_target.check_pattern}"
            except Exception as e:
                message = f"API检查失败: {str(e)}"
        
    except Exception as e:
        message = f"检查过程中发生错误: {str(e)}"
        logger.error(f"Error checking status for {monitor_target.name}: {str(e)}")
    
    # 计算响应时间
    response_time = (time.time() - start_time) * 1000  # 转换为毫秒
    
    return is_available, message, response_time

# 发送Telegram通知
def send_telegram_notification(chat_id, token, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logger.info(f"Telegram notification sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {str(e)}")
        return False

# 发送微信(息知)通知
def send_xi_zhi_notification(token, title, message):
    try:
        url = f"https://xizhi.qqoq.net/{token}.send"
        payload = {
            "title": title,
            "content": message
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()
        logger.info(f"Xi Zhi notification sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Xi Zhi notification: {str(e)}")
        return False

# 发送自定义URL通知
def send_webhook_notification(url, data):
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        logger.info(f"Webhook notification sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send webhook notification: {str(e)}")
        return False

# 发送通知
def send_notification(notification_setting, monitor_target, status_check):
    try:
        settings = notification_setting.settings or {}
        title = f"{monitor_target.name} 库存状态更新"
        
        if status_check.is_available:
            content = f"🎉 好消息！{monitor_target.name} 现在有库存了！\n\n" \
                     f"📅 检测时间: {status_check.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                     f"🔗 链接: {monitor_target.url}\n" \
                     f"💬 详情: {status_check.message}"
        else:
            content = f"😔 {monitor_target.name} 仍然没有库存\n\n" \
                     f"📅 检测时间: {status_check.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                     f"🔗 链接: {monitor_target.url}\n" \
                     f"💬 详情: {status_check.message}"
        
        if notification_setting.notification_type == 'telegram':
            token = settings.get('token', os.environ.get('TELEGRAM_BOT_TOKEN', ''))
            chat_id = settings.get('chat_id', '')
            if token and chat_id:
                send_telegram_notification(chat_id, token, content)
        
        elif notification_setting.notification_type == 'xi_zhi':
            token = settings.get('token', os.environ.get('XI_ZHI_TOKEN', ''))
            if token:
                send_xi_zhi_notification(token, title, content)
        
        elif notification_setting.notification_type == 'webhook':
            webhook_url = settings.get('url', '')
            if webhook_url:
                webhook_data = {
                    "monitor_name": monitor_target.name,
                    "url": monitor_target.url,
                    "is_available": status_check.is_available,
                    "timestamp": status_check.timestamp.isoformat(),
                    "message": status_check.message,
                    "response_time": status_check.response_time
                }
                send_webhook_notification(webhook_url, webhook_data)
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")

# 监控库存状态
def monitor_stock_status():
    with app.app_context():
        logger.info("Starting stock monitoring...")
        
        # 获取所有活跃的监控目标
        active_targets = MonitorTarget.query.filter_by(is_active=True).all()
        logger.info(f"Found {len(active_targets)} active monitor targets")
        
        for target in active_targets:
            logger.info(f"Checking stock status for: {target.name}")
            
            # 检查库存状态
            is_available, message, response_time = check_stock_status(target)
            
            # 创建状态检查记录
            status_check = StatusCheck(
                monitor_target_id=target.id,
                is_available=is_available,
                response_time=response_time,
                message=message
            )
            db.session.add(status_check)
            
            # 获取该监控目标的所有启用的通知设置
            notification_settings = NotificationSetting.query.filter_by(
                monitor_target_id=target.id,
                enabled=True
            ).all()
            
            # 检查是否需要发送通知（状态变化时）
            if notification_settings:
                # 获取上一次的状态检查结果
                previous_check = StatusCheck.query.filter_by(
                    monitor_target_id=target.id
                ).order_by(StatusCheck.timestamp.desc()).offset(1).first()
                
                # 如果是第一次检查或者状态发生变化，则发送通知
                if not previous_check or previous_check.is_available != is_available:
                    logger.info(f"Status changed for {target.name}, sending notifications")
                    for notification_setting in notification_settings:
                        send_notification(notification_setting, target, status_check)
            
        # 提交数据库更改
        db.session.commit()
        logger.info("Stock monitoring completed")

# 如果直接运行此脚本，立即执行一次监控
if __name__ == '__main__':
    # 导入app上下文
    from app import app
    monitor_stock_status()