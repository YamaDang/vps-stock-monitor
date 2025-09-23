import requests
import time
import json
import os
import random
from bs4 import BeautifulSoup
from threading import Lock

class StockMonitor:
    def __init__(self, config_path="data/config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.proxy_host = os.getenv('PROXY_HOST', '')
        self.lock = Lock()
        self.OUT_OF_STOCK_KEYWORDS = {'out of stock', '缺货', 'sold out', 'no stock', '缺貨中', '无货', '已售罄'}
        self.DEFAULT_HEADERS = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'max-age=0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        }
        self.USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"
        ]

    def load_config(self):
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return self._get_default_config()

    def _get_default_config(self):
        return {
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

    def save_config(self):
        with self.lock:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)

    def reload(self):
        new_config = self.load_config()
        with self.lock:
            self.config = new_config
        return "配置已重新加载"

    def check_stock(self, url, alert_class="alert alert-danger error-heading"):
        headers = self.DEFAULT_HEADERS.copy()
        headers['user-agent'] = random.choice(self.USER_AGENTS)
        
        try:
            if self.proxy_host:
                data = {
                    "cmd": "request.get",
                    "url": url,
                    "maxTimeout": 60000
                }
                response = requests.post(f'{self.proxy_host}/v1', json=data, headers=headers, timeout=15)
                result = response.json()
                
                if result.get('status') == 'ok':
                    content = result.get('solution', {}).get('response')
                else:
                    return None
            else:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 403 and not self.proxy_host:
                    return None
                content = response.text

            return self._judge_stock(content, alert_class)
            
        except Exception as e:
            print(f"检查库存时出错: {str(e)}")
            return None

    def _judge_stock(self, content, alert_class):
        if not content:
            return None
            
        if '宝塔防火墙正在检查您的访问' in content:
            return None
            
        soup = BeautifulSoup(content, 'html.parser')
        alert_elements = soup.select(f'.{alert_class.replace(" ", ".")}')
        
        if alert_elements:
            return False
            
        page_text = soup.get_text().lower()
        for keyword in self.OUT_OF_STOCK_KEYWORDS:
            if keyword.lower() in page_text:
                return False
                
        return True

    def send_message(self, message):
        config = self.config['config']
        notice_type = config.get('notice_type', 'telegram')
        
        try:
            if notice_type == 'telegram' and config.get('telegrambot') and config.get('chat_id'):
                url = f"https://api.telegram.org/bot{config['telegrambot']}/sendMessage"
                params = {
                    "chat_id": config['chat_id'],
                    "text": message
                }
                requests.get(url, params=params, timeout=10)
                
            elif notice_type == 'wechat' and config.get('wechat_key'):
                url = f"https://xizhi.qqoq.net/{config['wechat_key']}.send"
                params = {"text": "库存监控通知", "desp": message}
                requests.get(url, params=params, timeout=10)
                
            elif notice_type == 'custom' and config.get('custom_url'):
                url = config['custom_url'].replace('{message}', message)
                requests.get(url, timeout=10)
                
        except Exception as e:
            print(f"发送通知失败: {str(e)}")

    def update_stock_status(self):
        with self.lock:
            stocks = list(self.config['stock'].items())
            
        for name, item in stocks:
            status = self.check_stock(item['url'])
            if status is None:
                continue
                
            with self.lock:
                current_status = self.config['stock'][name].get('status', False)
                
            if status != current_status:
                message = f"📈 库存状态变化: {name}\n{status ? '✅ 有货' : '❌ 缺货'}\n{item['url']}"
                self.send_message(message)
                
                with self.lock:
                    self.config['stock'][name]['status'] = status
                    self.save_config()

    def start_monitoring(self):
        while True:
            self.update_stock_status()
            sleep_time = self.config['config'].get('frequency', 30)
            time.sleep(sleep_time)
