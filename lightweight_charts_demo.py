#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
运行 lightweight_charts.py 的启动脚本
"""

import os
import sys
import time
from lightweight_charts import create_app

def main():
    """启动 lightweight_charts.py"""
    print("=" * 80)
    print("正在启动TradingView Lightweight Charts演示应用...")
    print("请在浏览器中访问 http://127.0.0.1:8051/ 查看效果")
    print("=" * 80)
    
    try:
        # 创建并运行应用
        app = create_app()
        
        # 添加调试信息
        print("应用创建成功，准备启动...")
        print("如果您在浏览器中看到'LightweightCharts is not defined'错误，")
        print("请尝试刷新页面或清除浏览器缓存后重试。")
        print("=" * 80)
        
        # 运行应用
        app.run(debug=True, port=8051, dev_tools_props_check=False)
    except KeyboardInterrupt:
        print("\n应用程序已停止运行")
    except Exception as e:
        print(f"运行应用程序时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 