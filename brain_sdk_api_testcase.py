import logging
import time
import unittest

from brainflow import BoardShim, BrainFlowError
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
        logger.info('setUp')
        params = brainflow.BrainFlowInputParams()
        params.mac_address = self.mac_address
        params.timeout = self.timeout
        self.board_shim = BoardShim(self.board_id, params)

    def tearDown(self):
        logger.info('tearDown')
        if self.board_shim is not None:
            self.board_shim.release_session()
            self.board_shim = None

    def test_prepare_session(self):
        logger.info('test_prepare_session')
        try:
            self.board_shim.prepare_session()
            eeg_channels = self.board_shim.get_eeg_channels(self.board_id)
            self.assertGreaterEqual(len(eeg_channels), 1)
            logger.info("test_prepare_session: 会话准备成功，脑电通道数量验证通过")
        except BrainFlowError as e:
            logger.error(f"test_prepare_session: 脑flow业务异常，信息: {e}")
            self.fail(f"在test_prepare_session中出现脑flow业务异常: {e}")
        except Exception as e:
            logger.error(f"test_prepare_session: 其他运行时异常，信息: {e}")
            self.fail(f"在test_prepare_session中出现其他运行时异常: {e}")
        finally:
            self.board_shim.release_session()

    def test_start_stream(self):
        logger.info('test_start_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            if self.board_shim.is_streaming():
                logger.info("test_start_stream: 流启动成功")
            else:
                raise ValueError("流启动后但未处于正在流状态")
            self.board_shim.stop_stream()
        except BrainFlowError as e:
            logger.error(f"test_start_stream: 脑flow业务异常，信息: {e}")
            self.fail(f"在test_start_stream中出现脑flow业务异常: {e}")
        except Exception as e:
            logger.error(f"test_start_stream: 其他运行时异常，信息: {e}")
            self.fail(f"在test_start_stream中出现其他运行时异常: {e}")
        finally:
            self.board_shim.release_session()

    def test_get_sampling_rate(self):
        logger.info('test_get_sampling_rate')
        try:
            self.board_shim.prepare_session()
            sampling_rate = self.board_shim.get_sampling_rate()
            self.assertGreater(sampling_rate, 0)
            logger.info(f"test_get_sampling_rate: 获取采样率成功，采样率为 {sampling_rate}")
        except BrainFlowError as e:
            logger.error(f"test_get_sampling_rate: 脑flow业务异常，信息: {e}")
            self.fail(f"在test_get_sampling_rate中出现脑flow业务异常: {e}")
        except Exception as e:
            logger.error(f"test_get_sampling_rate: 其他运行时异常，信息: {e}")
            self.fail(f"在test_get_sampling_rate中出现其他运行时异常: {e}")
        finally:
            self.board_shim.release_session()

    def test_get_board_data(self):
        logger.info('test_get_board_data')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            time.sleep(1)
            data = self.board_shim.get_board_data()
            self.assertEqual(len(data), self.board_shim.get_num_rows())
            logger.info("test_get_board_data: 获取板卡数据成功")
        except BrainFlowError as e:
            logger.error(f"test_get_board_data: 脑flow业务异常，信息: {e}")
            self.fail(f"在test_get_board_data中出现脑flow业务异常: {e}")
        except Exception as e:
            logger.error(f"test_get_board_data: 其他运行时异常，信息: {e}")
            self.fail(f"在test_get_board_data中出现其他运行时异常: {e}")
        finally:
            self.board_shim.stop_stream()
            self.board_shim.release_session()

    def test_stop_stream(self):
        logger.info('test_stop_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            self.board_shim.stop_stream()
            if not self.board_shim.is_streaming():
                logger.info("test_stop_stream: 流停止成功")
            else:
                raise ValueError("调用停止流方法后，流仍未停止")
        except BrainFlowError as e:
            logger.error(f"test_stop_stream: 脑flow业务异常，信息: {e}")
            self.fail(f"在test_stop_stream中出现脑flow业务异常: {e}")
        except Exception as e:
            logger.error(f"test_stop_stream: 其他运行时异常，信息: {e}")
            self.fail(f"在test_stop_stream中出现其他运行时异常: {e}")
        finally:
            self.board_shim.release_session()

    def test_release_session(self):
        logger.info('test_release_session')
        try:
            self.board_shim.prepare_session()
            self.board_shim.release_session()
            logger.info("test_release_session: 会话释放成功")
        except BrainFlowError as e:
            logger.error(f"test_release_session: 脑flow业务异常，信息: {e}")
            self.fail(f"在test_release_session中出现脑flow业务异常: {e}")
        except Exception as e:
            logger.error(f"test_release_session: 其他运行时异常，信息: {e}")
            self.fail(f"在test_release_session中出现其他运行时异常: {e}")
        finally:
            self.board_shim = None


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
    logger.error(f"测试方法 {test_method_name} 失败，失败信息: {failure_message}")


def handle_error_result(test_method_name, error_message):
    logger.error(f"测试方法 {test_method_name} 出现错误，错误信息: {error_message}")


def handle_skipped_result(test_method_name, reason):
    logger.info(f"测试方法 {test_method_name} 被跳过，原因: {reason}")


def handle_successful_result():
    logger.info("所有测试成功执行完毕")


if __name__ == '__main__':
    mac_address = 'C4:64:E3:D8:E6:D2'
    board_id = 57
    main(mac_address=mac_address, board_id=board_id)