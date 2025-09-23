import requests
import time
import json
import os
import random
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/monitor.log"),
        logging.StreamHandler()
    ]
)

class StockMonitor:
    # 配置默认值常量
    DEFAULT_CONFIG = {
        "config": {
            "frequency": 30,
            "telegrambot": "",
            "chat_id": "",
            "notice_type": "telegram",
            "wechat_key": "",
            "custom_url": ""
        },
        "stock": {}
    }
    
    # 请求头常量
    DEFAULT_HEADERS = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'upgrade-insecure-requests': '1',
    }
    
    # 缺货关键词常量
    OUT_OF_STOCK_KEYWORDS = {'out of stock', '缺货', 'sold out', 'no stock', '缺貨中', '无货', '已售罄'}
    
    # 用户代理池
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/113.0"
    ]

    def __init__(self, config_path="data/config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.proxy_host = os.getenv('PROXY_HOST', '')
        self.running = True
        self.last_notify_time = {}  # 记录每个商品的最后通知时间，避免频繁通知

    def load_config(self):
        """加载配置文件，若不存在则创建默认配置"""
        try:
            # 确保数据目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 验证配置结构，确保所有必要字段存在
                    return self._validate_config(config)
            else:
                # 创建默认配置
                self.save_config(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG
        except Exception as e:
            logging.error(f"加载配置失败: {str(e)}")
            return self.DEFAULT_CONFIG

    def _validate_config(self, config):
        """验证并补全配置结构"""
        # 确保config和stock字段存在
        if 'config' not in config:
            config['config'] = self.DEFAULT_CONFIG['config']
        if 'stock' not in config:
            config['stock'] = self.DEFAULT_CONFIG['stock']
            
        # 补全缺失的配置项
        for key, value in self.DEFAULT_CONFIG['config'].items():
            if key not in config['config']:
                config['config'][key] = value
                
        # 补全库存项中的缺失字段
        for name, item in config['stock'].items():
            if 'status' not in item:
                item['status'] = False
            if 'url' not in item:
                item['url'] = ''
                
        return config

    def save_config(self, config=None):
        """保存配置到文件"""
        try:
            if config is None:
                config = self.config
                
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logging.info("配置已保存")
        except Exception as e:
            logging.error(f"保存配置失败: {str(e)}")

    def reload(self):
        """重新加载配置"""
        logging.info("重新加载配置...")
        self.config = self.load_config()

    def _get_random_headers(self):
        """获取随机请求头"""
        headers = self.DEFAULT_HEADERS.copy()
        headers['user-agent'] = random.choice(self.USER_AGENTS)
        return headers

    def _fetch_content(self, url):
        """获取网页内容，支持代理"""
        try:
            headers = self._get_random_headers()
            
            # 先尝试直接请求
            response = requests.get(url, headers=headers, timeout=10)
            
            # 如果遇到403且配置了代理，使用代理重试
            if response.status_code == 403 and self.proxy_host:
                logging.warning(f"直接请求 {url} 被拒绝，尝试使用代理...")
                data = {
                    "cmd": "request.get",
                    "url": url,
                    "maxTimeout": 60000
                }
                response = requests.post(
                    f"{self.proxy_host}/v1",
                    headers={"Content-Type": "application/json"},
                    json=data,
                    timeout=15
                )
                result = response.json()
                if result.get("status") == "ok":
                    return result.get("solution", {}).get("response")
                else:
                    logging.error(f"代理请求失败: {result.get('message')}")
                    return None
            
            response.raise_for_status()  # 抛出HTTP错误
            return response.text
            
        except requests.exceptions.RequestException as e:
            logging.error(f"请求 {url} 失败: {str(e)}")
            return None

    def _judge_stock(self, content, alert_class="alert alert-danger error-heading"):
        """判断库存状态"""
        if not content:
            return None
            
        # 检测是否遇到宝塔防火墙
        if '宝塔防火墙正在检查您的访问' in content:
            logging.warning("检测到宝塔防火墙，无法判断库存状态")
            return None
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # 方法1: 检查特定class的元素
        alert_elements = soup.find_all(class_=alert_class)
        if alert_elements:
            for element in alert_elements:
                text = element.get_text().lower()
                if any(keyword in text for keyword in self.OUT_OF_STOCK_KEYWORDS):
                    return False  # 缺货
        
        # 方法2: 检查页面中是否包含缺货关键词
        page_text = soup.get_text().lower()
        for keyword in self.OUT_OF_STOCK_KEYWORDS:
            if keyword in page_text:
                return False  # 缺货
                
        return True  # 有货

    def check_stock(self, url, alert_class="alert alert-danger error-heading"):
        """检查指定URL的库存状态"""
        content = self._fetch_content(url)
        if not content:
            return None
        return self._judge_stock(content, alert_class)

    def _send_telegram(self, message):
        """发送Telegram通知"""
        token = self.config['config'].get('telegrambot')
        chat_id = self.config['config'].get('chat_id')
        
        if not token or not chat_id:
            logging.warning("Telegram配置不完整，无法发送通知")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            params = {
                "chat_id": chat_id,
                "text": message
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            logging.info("Telegram通知发送成功")
            return True
        except Exception as e:
            logging.error(f"Telegram通知发送失败: {str(e)}")
            return False

    def _send_wechat(self, message):
        """发送微信通知（通过息知）"""
        wechat_key = self.config['config'].get('wechat_key')
        
        if not wechat_key:
            logging.warning("微信配置不完整，无法发送通知")
            return False
            
        try:
            url = f"https://xizhi.qqoq.net/{wechat_key}.send"
            params = {"text": "库存状态通知", "desp": message}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            logging.info("微信通知发送成功")
            return True
        except Exception as e:
            logging.error(f"微信通知发送失败: {str(e)}")
            return False

    def _send_custom(self, message):
        """发送自定义URL通知"""
        custom_url = self.config['config'].get('custom_url')
        
        if not custom_url or "{message}" not in custom_url:
            logging.warning("自定义通知URL配置不完整，无法发送通知")
            return False
            
        try:
            url = custom_url.replace("{message}", requests.utils.quote(message))
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            logging.info("自定义URL通知发送成功")
            return True
        except Exception as e:
            logging.error(f"自定义URL通知发送失败: {str(e)}")
            return False

    def send_message(self, message):
        """根据配置发送通知"""
        notice_type = self.config['config'].get('notice_type', 'telegram')
        
        handlers = {
            'telegram': self._send_telegram,
            'wechat': self._send_wechat,
            'custom': self._send_custom
        }
        
        handler = handlers.get(notice_type)
        if handler:
            return handler(message)
        else:
            logging.error(f"不支持的通知类型: {notice_type}")
            return False

    def update_stock_status(self):
        """更新所有监控项的库存状态"""
        stock_changed = False
        current_time = time.time()
        
        for name, item in self.config['stock'].items():
            try:
                url = item.get('url')
                if not url:
                    continue
                    
                logging.info(f"检查 {name} 的库存状态...")
                status = self.check_stock(url)
                
                if status is None:  # 无法判断状态
                    continue
                    
                # 状态有变化
                if status != item['status']:
                    stock_changed = True
                    old_status = "有货" if item['status'] else "缺货"
                    new_status = "有货" if status else "缺货"
                    
                    # 更新状态
                    item['status'] = status
                    item['last_changed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 记录日志
                    logging.info(f"{name} 库存状态变化: {old_status} → {new_status}")
                    
                    # 发送通知（控制频率，至少间隔5分钟）
                    message = f"📢 {name} 库存状态变化\n状态: {old_status} → {new_status}\n链接: {url}"
                    last_time = self.last_notify_time.get(name, 0)
                    
                    if current_time - last_time > 300:  # 5分钟
                        self.send_message(message)
                        self.last_notify_time[name] = current_time
                    
            except Exception as e:
                logging.error(f"处理 {name} 时出错: {str(e)}")
        
        # 如果有状态变化，保存配置
        if stock_changed:
            self.save_config()
            
        return stock_changed

    def start_monitoring(self):
        """开始监控循环"""
        logging.info("开始库存监控...")
        self.running = True
        
        while self.running:
            try:
                # 检查并更新库存状态
                self.update_stock_status()
                
                # 等待配置的时间间隔（秒）
                sleep_time = int(self.config['config'].get('frequency', 30))
                logging.info(f"等待 {sleep_time} 秒后再次检查...")
                time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"监控循环出错: {str(e)}")
                time.sleep(10)  # 出错后等待10秒再重试

    def stop_monitoring(self):
        """停止监控循环"""
        logging.info("停止库存监控...")
        self.running = False
    