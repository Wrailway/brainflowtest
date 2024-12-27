import logging
import time
import unittest

from brainflow import BoardShim
import brainflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSDKApi(unittest.TestCase):
    def __init__(self, mac_address: str, board_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_address = mac_address
        self.board_id = board_id
        self.timeout = 40

    def setUp(self):
        params = brainflow.BrainFlowInputParams()
        params.mac_address = self.mac_address
        params.timeout = self.timeout
        self.board_shim = BoardShim(self.board_id, params)

    def tearDown(self):
        self.board_shim = None

    def test_prepare_session(self):
        try:
            self.board_shim.prepare_session()
            eeg_channels = self.board_shim.get_eeg_channels(self.board_id)
            self.assertGreaterEqual(len(eeg_channels), 1)
        except Exception as e:
            self.fail(f"在test_prepare_session中出现异常: {e}")  # 使用self.fail来标记测试失败并输出异常信息
        finally:
            self.board_shim.release_session()

    def test_start_stream(self):
        # 这里添加具体的测试逻辑，用于测试start_stream方法，暂时留空示例
        pass

    def test_get_sampling_rate(self):
        # 这里添加具体的测试逻辑，用于测试get_sampling_rate方法，暂时留空示例
        pass

    def test_get_board_data(self):
        # 这里添加具体的测试逻辑，用于测试get_board_data方法，暂时留空示例
        pass

    def test_stop_stream(self):
        # 这里添加具体的测试逻辑，用于测试stop_stream方法，暂时留空示例
        pass

    def test_release_session(self):
        # 这里添加具体的测试逻辑，用于测试release_session方法，暂时留空示例
        pass


def main(mac_address: str, board_id: int):
    start_time = time.time()
    test_result = '不通过'
    TempTestClass = type('TempTest', (TestSDKApi,), {'__init__': lambda self, *args, **kwargs: TestSDKApi.__init__(self, mac_address, board_id, *args, **kwargs)})

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    tests = loader.loadTestsFromTestCase(TempTestClass)
    suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

   
    # 处理测试失败情况
    for failure in result.failures:
        test_method_name, failure_message = failure
        handle_failure_result(test_method_name, failure_message)

    # 处理测试错误情况（一般是代码层面错误导致测试无法正确执行）
    for error in result.errors:
        test_method_name, error_message = error
        handle_error_result(test_method_name, error_message)

    # 处理测试跳过情况
    for skipped_test in result.skipped:
        test_method_name, reason = skipped_test
        handle_skipped_result(test_method_name, reason)

    # 处理测试成功情况
    # handle_successful_result(port_result, result, timestamp)

    if result.wasSuccessful():
        logger.info("All tests passed successfully.\n")
        test_result = '通过'
    else:
        logger.info("Some tests failed or encountered errors.\n")
        test_result = '不通过'

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"\n\n Ran {result.testsRun} tests in {elapsed_time:.3f}s,测试结果是:{test_result}\n")
    
def handle_failure_result(test_method_name, failure_message):
    pass


def handle_error_result(test_method_name, error_message):
    pass


def handle_skipped_result(test_method_name, reason):
    pass


def handle_successful_result(result):
    pass


if __name__ == '__main__':
    mac_address = 'C4:64:E3:D8:E6:D2'
    board_id = 57
    main(mac_address=mac_address, board_id=board_id)
    