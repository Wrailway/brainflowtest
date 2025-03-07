import subprocess
import time
import webbrowser
import socket

def run_pytest():
    """
    执行 pytest 测试并将结果保存到 allure-results 目录
    """
    print("开始执行 pytest 测试...")
    try:
        subprocess.run(['pytest', '-v', '-s', 'test_brain_sdk_api.py', '--alluredir=allure-results'], check=True)
        print("pytest 测试执行完成")
    except subprocess.CalledProcessError as e:
        print(f"pytest 测试执行失败: {e}")

def generate_allure_report():
    """
    依据 allure-results 目录下的结果生成 Allure 报告
    """
    print("开始生成 Allure 报告...")
    allure_path = r"D:\software\allure-2.32.0\allure-2.32.0\bin\allure.bat"  # 根据实际安装路径修改
    try:
        subprocess.run([allure_path, 'generate', 'allure-results', '-o', 'allure-report', '--clean'], check=True)
        print("Allure 报告生成完成")
    except subprocess.CalledProcessError as e:
        print(f"Allure 报告生成失败: {e}")

def start_allure_server():
    """
    启动 Allure 服务器并等待其启动
    """
    print("启动 Allure 服务器...")
    allure_path = r"D:\software\allure-2.32.0\allure-2.32.0\bin\allure.bat"  # 根据实际安装路径修改
    server_process = subprocess.Popen([allure_path, 'serve', 'allure-results', '-p', '8081'])
    # 等待服务器启动
    max_retries = 30
    retries = 0
    while retries < max_retries:
        try:
            with socket.create_connection(('localhost', 8081), timeout=1):
                print("Allure 服务器已启动")
                break
        except (ConnectionRefusedError, OSError):
            retries += 1
            time.sleep(1)
    else:
        print("Allure 服务器启动失败，超时等待")
        server_process.terminate()
        raise TimeoutError("Allure 服务器启动超时")
    return server_process

def open_browser():
    """
    使用默认浏览器打开 Allure 报告页面
    """
    url = "http://localhost:8081"
    print(f"打开浏览器访问 Allure 报告页面: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    run_pytest()
    generate_allure_report()
    try:
        server_process = start_allure_server()
        open_browser()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("用户手动终止，停止 Allure 服务器...")
            server_process.terminate()
    except Exception as e:
        print(f"启动 Allure 服务器或打开浏览器时出现错误: {e}")