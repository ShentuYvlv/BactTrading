"""
币安交易复盘工具启动脚本
"""
import os
import sys
import subprocess

def main():
    """
    启动币安交易复盘工具
    """
    print("正在启动币安交易复盘工具...")
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(current_dir, "app.py")
    
    # 检查app.py是否存在
    if not os.path.exists(app_path):
        print(f"错误: 找不到应用程序文件 {app_path}")
        sys.exit(1)
    
    try:
        # 运行应用程序
        subprocess.run([sys.executable, app_path], check=True)
    except KeyboardInterrupt:
        print("\n应用程序已停止运行")
    except Exception as e:
        print(f"运行应用程序时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 