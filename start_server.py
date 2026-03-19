#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动局域网可访问的交易图表服务器
"""

import socket
from lightweight_charts import create_app
from config import get_server_config

def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        # 创建一个UDP socket连接到外部地址来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def check_port_available(port):
    """检查端口是否可用"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', port))
        s.close()
        return True
    except OSError:
        return False

def main():
    """主函数"""
    print("🚀 启动交易图表服务器")
    print("="*60)

    server_config = get_server_config()
    
    # 获取本机IP
    local_ip = get_local_ip()
    port = server_config['port']
    
    # 检查端口是否可用
    if not check_port_available(port):
        print(f"⚠️ 端口 {port} 已被占用，尝试使用其他端口...")
        for test_port in range(port + 1, server_config['port_fallback_end'] + 1):
            if check_port_available(test_port):
                port = test_port
                break
        else:
            print("❌ 找不到可用端口，请手动指定端口")
            return
    
    print(f"📡 服务器配置:")
    print(f"   本机IP: {local_ip}")
    print(f"   端口: {port}")
    print(f"   调试模式: {'开启' if server_config['debug'] else '关闭'}")
    
    print(f"\n🌐 访问地址:")
    print(f"   本机访问: http://127.0.0.1:{port}")
    print(f"   局域网访问: http://{local_ip}:{port}")
    
    print(f"\n📱 局域网内其他设备访问方法:")
    print(f"   1. 确保所有设备连接到同一个WiFi/局域网")
    print(f"   2. 在其他设备的浏览器中输入: http://{local_ip}:{port}")
    print(f"   3. 手机、平板、其他电脑都可以访问")
    
    print(f"\n🔧 防火墙设置:")
    print(f"   如果无法访问，请检查Windows防火墙设置")
    print(f"   允许Python程序通过防火墙")
    print(f"   或临时关闭防火墙进行测试")
    
    print(f"\n🔍 网络诊断:")
    print(f"   如果其他设备无法访问，可以尝试:")
    print(f"   1. ping {local_ip} (测试网络连通性)")
    print(f"   2. telnet {local_ip} {port} (测试端口连通性)")
    
    print(f"\n" + "="*60)
    print(f"🎯 正在启动服务器...")
    print(f"💡 按 Ctrl+C 停止服务器")
    print(f"="*60)
    
    try:
        # 创建并启动应用
        app = create_app()
        app.run(
            debug=server_config['debug'],
            host=server_config['host'],
            port=port,
            use_reloader=server_config['use_reloader']
        )
    except KeyboardInterrupt:
        print(f"\n🛑 服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print(f"💡 请检查端口是否被占用或防火墙设置")

if __name__ == "__main__":
    main()
