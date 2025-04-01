import subprocess
import time
import webbrowser
import socket
import shutil

# 动态获取 Allure 路径
ALLURE_PATH = shutil.which('allure')
if ALLURE_PATH is None:
    print("未找到 Allure，请确保 Allure 已安装并配置到环境变量中。")
    exit(1)

TEST_FILE = 'test_synchroni_sdk_api.py'
RESULT_DIR = 'allure-results'
REPORT_DIR = 'allure-report'
SERVER_PORT = 8081
SERVER_URL = f"http://localhost:{SERVER_PORT}"


def run_pytest():
    """
    执行 pytest 测试并将结果保存到 allure-results 目录
    """
    print("开始执行 pytest 测试...")
    try:
        subprocess.run(['pytest', '-v', '-s', TEST_FILE, f'--alluredir={RESULT_DIR}'], check=False)
        print("pytest 测试执行完成")
    except Exception as e:
        print(f"pytest 测试执行过程中出现错误: {e}")


def generate_allure_report():
    """
    依据 allure-results 目录下的结果生成 Allure 报告
    """
    print("开始生成 Allure 报告...")
    try:
        subprocess.run([ALLURE_PATH, 'generate', RESULT_DIR, '-o', REPORT_DIR, '--clean'], check=True)
        print("Allure 报告生成完成")
    except subprocess.CalledProcessError as e:
        print(f"Allure 报告生成失败: {e}")
        raise


def is_server_running():
    """
    检查 Allure 服务器是否正在运行
    """
    try:
        with socket.create_connection(('localhost', SERVER_PORT), timeout=1):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def start_allure_server():
    """
    启动 Allure 服务器并等待其启动
    """
    print("启动 Allure 服务器...")
    server_process = subprocess.Popen([ALLURE_PATH, 'serve', RESULT_DIR, '-p', str(SERVER_PORT)])
    max_retries = 30
    retries = 0
    while retries < max_retries:
        if is_server_running():
            print("Allure 服务器已启动")
            break
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
    print(f"打开浏览器访问 Allure 报告页面: {SERVER_URL}")
    webbrowser.open(SERVER_URL)


def main():
    run_pytest()
    try:
        generate_allure_report()
        server_process = start_allure_server()
        open_browser()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("用户手动终止，停止 Allure 服务器...")
            server_process.terminate()
    except Exception as e:
        print(f"执行过程中出现错误: {e}")


if __name__ == "__main__":
    main()