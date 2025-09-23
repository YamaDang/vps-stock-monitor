import requests
import time
import json
import os
import random
from bs4 import BeautifulSoup
from threading import Lock

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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0"
    ]
    
    def __init__(self, config_path="data/config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.proxy_host = os.environ.get('PROXY_HOST', '')
        self.running = False
        self.lock = Lock()
        print("StockMonitor initialized")

    def load_config(self):
        """加载配置文件，如不存在则创建默认配置"""
        try:
            if not os.path.exists(self.config_path):
                # 确保目录存在
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                # 创建默认配置
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
                return self.DEFAULT_CONFIG.copy()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证配置并补充缺失的默认值
            self._validate_and_update_config(config)
            return config
        except Exception as e:
            print(f"加载配置失败: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _validate_and_update_config(self, config):
        """验证配置并补充缺失的默认值"""
        # 确保config和stock节点存在
        if 'config' not in config:
            config['config'] = self.DEFAULT_CONFIG['config'].copy()
        if 'stock' not in config:
            config['stock'] = self.DEFAULT_CONFIG['stock'].copy()
            
        # 补充缺失的配置项
        for key, value in self.DEFAULT_CONFIG['config'].items():
            if key not in config['config']:
                config['config'][key] = value
                
        # 验证监控项
        for name, item in config['stock'].items():
            if 'url' not in item:
                print(f"警告: 监控项 '{name}' 缺少URL，已移除")
                del config['stock'][name]
            if 'status' not in item:
                item['status'] = False

    def save_config(self):
        """保存配置到文件"""
        try:
            with self.lock:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置失败: {e}")

    def reload(self):
        """重新加载配置"""
        print("重新加载配置...")
        new_config = self.load_config()
        with self.lock:
            self.config = new_config
        print("配置已重新加载")

    def start_monitoring(self):
        """开始监控库存"""
        self.running = True
        print("开始监控库存...")
        while self.running:
            try:
                self.update_stock_status()
                # 获取监控频率，确保是合理的数值
                frequency = max(10, int(self.config['config'].get('frequency', 30)))
                time.sleep(frequency)
            except Exception as e:
                print(f"监控循环出错: {e}")
                time.sleep(10)

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        print("监控已停止")

    def update_stock_status(self):
        """更新所有监控项的库存状态"""
        with self.lock:
            stocks = list(self.config['stock'].items())
            
        if not stocks:
            print("没有监控项，跳过检查")
            return

        print(f"开始检查 {len(stocks)} 个监控项的库存状态...")
        for name, item in stocks:
            try:
                current_status = self.check_stock(item['url'])
                if current_status is None:
                    print(f"无法检查 {name} 的库存状态")
                    continue
                    
                # 状态变化时发送通知
                if current_status != item['status']:
                    print(f"{name} 库存状态变化: {'有货' if current_status else '缺货'}")
                    message = f"{name} 库存状态变化: {'现在有货了！' if current_status else '现已缺货！'}\n链接: {item['url']}"
                    self.send_message(message)
                    
                    # 更新状态
                    with self.lock:
                        self.config['stock'][name]['status'] = current_status
                    self.save_config()
                else:
                    print(f"{name} 库存状态未变: {'有货' if current_status else '缺货'}")
            except Exception as e:
                print(f"检查 {name} 时出错: {e}")

    def check_stock(self, url):
        """检查单个URL的库存状态"""
        content = self._fetch_content(url)
        if not content:
            return None
            
        return self._judge_stock(content)

    def _fetch_content(self, url):
        """获取网页内容，支持代理"""
        headers = self.DEFAULT_HEADERS.copy()
        headers['user-agent'] = random.choice(self.USER_AGENTS)
        
        try:
            # 尝试直接请求
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 检查是否被Cloudflare拦截
            if response.status_code == 403 or 'cloudflare' in response.text.lower():
                print(f"访问 {url} 被拦截，尝试使用代理...")
                return self._fetch_through_proxy(url, headers)
                
            return response.text
            
        except Exception as e:
            print(f"直接请求 {url} 失败: {e}")
            if self.proxy_host:
                return self._fetch_through_proxy(url, headers)
            return None

    def _fetch_through_proxy(self, url, headers):
        """通过代理获取网页内容"""
        if not self.proxy_host:
            print("未配置代理，无法绕过拦截")
            return None
            
        try:
            data = {
                "cmd": "request.get",
                "url": url,
                "headers": headers,
                "maxTimeout": 60000
            }
            
            response = requests.post(f"{self.proxy_host}/v1", json=data, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") == "ok":
                return result.get("solution", {}).get("response")
            else:
                print(f"代理请求失败: {result.get('message')}")
                return None
                
        except Exception as e:
            print(f"代理请求 {url} 失败: {e}")
            return None

    def _judge_stock(self, content):
        """判断库存状态"""
        # 检查是否有特殊拦截页面
        if '宝塔防火墙正在检查您的访问' in content:
            print("检测到宝塔防火墙拦截")
            return None
            
        soup = BeautifulSoup(content, 'html.parser')
        page_text = soup.get_text().lower()
        
        # 检查缺货关键词
        for keyword in self.OUT_OF_STOCK_KEYWORDS:
            if keyword in page_text:
                return False
                
        # 检查特定缺货标识
        alert_classes = [
            "alert alert-danger error-heading",
            "out-of-stock",
            "stock-status out-of-stock"
        ]
        
        for alert_class in alert_classes:
            if soup.find(class_=alert_class):
                return False
                
        return True

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
            try:
                handler(message)
                print(f"通知已发送: {message[:30]}...")
            except Exception as e:
                print(f"发送{notice_type}通知失败: {e}")
        else:
            print(f"不支持的通知类型: {notice_type}")

    def _send_telegram(self, message):
        """发送Telegram通知"""
        token = self.config['config'].get('telegrambot')
        chat_id = self.config['config'].get('chat_id')
        
        if not token or not chat_id:
            raise ValueError("Telegram配置不完整（缺少token或chat_id）")
            
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        params = {
            "chat_id": chat_id,
            "text": message
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if not result.get("ok"):
            raise Exception(f"Telegram API错误: {result.get('description')}")

    def _send_wechat(self, message):
        """发送微信通知（通过息知）"""
        wechat_key = self.config['config'].get('wechat_key')
        
        if not wechat_key:
            raise ValueError("微信配置不完整（缺少息知KEY）")
            
        url = f"https://xizhi.qqoq.net/{wechat_key}.send"
        params = {
            "title": "库存状态通知",
            "content": message
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") != 200:
            raise Exception(f"微信通知错误: {result.get('msg')}")

    def _send_custom(self, message):
        """发送自定义URL通知"""
        custom_url = self.config['config'].get('custom_url')
        
        if not custom_url:
            raise ValueError("自定义通知配置不完整（缺少URL）")
            
        # 替换URL中的占位符
        url = custom_url.replace("{message}", requests.utils.quote(message))
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    