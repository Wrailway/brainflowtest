import logging
import threading
import time
import unittest

from brainflow import BoardIds, BoardShim, BrainFlowError
import brainflow
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


import unittest
import logging
import brainflow
from brainflow.board_shim import BoardShim, BrainFlowError
import time

# 设置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# 获取当前时间的时间戳（精确到秒）
timestamp = str(int(time.time()))
# 获取当前日期，格式为年-月-日
current_date = time.strftime("%Y-%m-%d", time.localtime())
# 构建完整的文件名，包含路径、日期和时间戳
log_file_name = f'./TestSDKApi_log_{current_date}_{timestamp}.txt'

# 创建一个文件处理器，用于将日志写入文件
file_handler = logging.FileHandler(log_file_name,encoding='utf-8')
file_handler.setLevel(logging.INFO)

# 创建一个日志格式
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)

# 将文件处理器添加到日志记录器
logger.addHandler(file_handler)

class TestSDKApi(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_id = 57
        self.board_id2 = 58
        self.mac_address = 'C4:64:E3:D8:E6:D2'
        self.mac_address2 = 'C4:64:E3:D8:E3:EE'
        self.timeout = 10
        # 以下为测试常数定义部分
        self.CHANNEL_NUM = 2  # 不同产品的通道数目有区分，这里假设真实值是7
        self.CHANNEL_NUM2 = 7
        self.SAMPLING_RATE = 250  # 根据产品定义的实际采样率，假设真实值是250
        self.SAMPLING_RATE2 = 250
        
    def is_skip_concurrent():
        return True

    def setUp(self):
        logger.info('setUp')
        self.board_shim = self.init_board_shim(self.board_id, self.mac_address)
        if TestSDKApi.is_skip_concurrent():
            self.board_shim2 = self.init_board_shim(self.board_id2, self.mac_address2)

    def tearDown(self):
        logger.info('tearDown')
        self.board_shim = None
        if TestSDKApi.is_skip_concurrent():
            self.board_shim2 = None

    def init_board_shim(self, board_id, mac_address):
        """
        初始化BoardShim对象的公共方法
        """
        params = brainflow.BrainFlowInputParams()
        params.mac_address = mac_address
        params.timeout = self.timeout
        return BoardShim(board_id, params)

    def test_prepare_session(self):
        logger.info('test_prepare_session')
        try:
            self.board_shim.prepare_session()
            eeg_channels = self.board_shim.get_eeg_channels(self.board_id)
            self.assertGreaterEqual(len(eeg_channels), self.CHANNEL_NUM)
            self.assertEqual(self.board_shim.is_prepared(), True)
            logger.info("test_prepare_session: 会话准备成功，脑电通道数量及其他验证通过")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_prepare_session", e)
        except Exception as e:
            self.handle_general_exception("test_prepare_session", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()

    def test_start_stream(self):
        logger.info('test_start_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            data = self.board_shim.get_board_data()
            self.assertEqual(len(data), self.board_shim.get_num_rows(board_id=self.board_id))
            logger.info("test_start_stream: 流启动成功，数据验证通过")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_start_stream", e)
        except Exception as e:
            self.handle_general_exception("test_start_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()

    def test_get_sampling_rate(self):
        logger.info('test_get_sampling_rate')
        try:
            self.board_shim.prepare_session()
            sampling_rate = self.board_shim.get_sampling_rate(board_id=self.board_id)
            self.assertEqual(sampling_rate, self.SAMPLING_RATE)
            logger.info(f"test_get_sampling_rate: 获取采样率成功，采样率为 {sampling_rate}")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_get_sampling_rate", e)
        except Exception as e:
            self.handle_general_exception("test_get_sampling_rate", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()

    def test_get_board_data(self):
        logger.info('test_get_board_data')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            time.sleep(1)
            data = self.board_shim.get_board_data()
            self.assertEqual(len(data), self.board_shim.get_num_rows(board_id=self.board_id))
            logger.info("test_get_board_data: 获取板卡数据成功")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_get_board_data", e)
        except Exception as e:
            self.handle_general_exception("test_get_board_data", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()

            
    @unittest.skip('停流后，仍然能获取到数据，该条case暂时跳过，已反馈给研发分析')
    def test_stop_stream(self):
        logger.info('test_stop_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            self.board_shim.stop_stream()
            data = self.board_shim.get_board_data()
            self.assertNotEqual(len(data), self.board_shim.get_num_rows(board_id=self.board_id))
            logger.info("test_stop_stream: 流停止成功，资源释放验证通过")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_stop_stream", e)
        except Exception as e:
            self.handle_general_exception("test_stop_stream", e)
        finally:
             if self.board_shim.is_prepared():
                self.board_shim.release_session()

    def test_release_session(self):
        logger.info('test_release_session')
        try:
            self.board_shim.prepare_session()
            self.board_shim.release_session()
            self.assertEqual(self.board_shim.is_prepared(), False)
            logger.info("test_release_session: 会话释放成功")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_release_session", e)
        except Exception as e:
            self.handle_general_exception("test_release_session", e)
            
    def test_invalid_mac_address(self):
        logger.info('test_invalid_mac_address')
        invalid_mac = "invalid_mac_address"
        try:
            params = brainflow.BrainFlowInputParams()
            params.mac_address = invalid_mac
            params.timeout = self.timeout
            board_shim = BoardShim(self.board_id, params)
            board_shim.prepare_session()
            self.fail("使用无效MAC地址时应抛出异常，但未抛出")
        except BrainFlowError as e:
            self.assertEqual(e.exit_code, brainflow.BrainFlowExitCodes.BOARD_NOT_CREATED_ERROR)  # 替换为实际对应的错误码判断
            logger.info("test_invalid_mac_address: 无效MAC地址异常验证通过")
        except Exception as e:
            self.handle_general_exception("test_invalid_mac_address", e)

    def test_timeout_scenario(self):
        logger.info('test_timeout_scenario')
        params = brainflow.BrainFlowInputParams()
        params.timeout = 1  # 设置一个很短的超时时间，容易触发超时情况
        params.mac_address =self.mac_address
        board_shim = BoardShim(self.board_id,params)
        try:
            board_shim.prepare_session()
            self.fail("应出现超时异常，但未出现")
        except BrainFlowError as e:
            if e.exit_code == brainflow.BrainFlowExitCodes.BOARD_NOT_READY_ERROR:  # 根据实际的错误类型判断是否是超时异常
                logger.info("test_timeout_scenario: 超时异常验证通过")
            else:
                self.handle_brainflow_error("test_timeout_scenario", e)
        except Exception as e:
            self.handle_general_exception("test_timeout_scenario", e)
        finally:
            # self.release_board_shim(board_shim)
            pass


    def test_data_format_verification(self):
        logger.info('test_data_format_verification')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            data = self.board_shim.get_board_data()
            # 假设数据应该是二维数组，进行格式验证
            self.assertEqual(len(data.shape), 2)
            # 假设数据类型应该是float32，进行数据类型验证（根据实际情况调整）
            self.assertEqual(data.dtype, np.float64)
            logger.info("test_data_format_verification: 数据格式验证通过")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_data_format_verification", e)
        except Exception as e:
            self.handle_general_exception("test_data_format_verification", e)
        finally:
                if self.board_shim.is_prepared():
                    self.board_shim.stop_stream()
                    self.board_shim.release_session()
            
    def test_get_data_without_start_stream(self):
        logger.info('tes_get_data_without_start_stream')
        try:
            self.board_shim.prepare_session()
            data = self.board_shim.get_board_data()
            self.fail('stream is not startted or no preset,cannot get data')
        except BrainFlowError as e:
            if e.exit_code == brainflow.BrainFlowExitCodes.INVALID_ARGUMENTS_ERROR:
                logger.info('test_get_data_without_start_stream:未开启流，无法获取数据验证通过')
            else:
                # self.handle_brainflow_error("test_get_data_without_start_stream", e)
                self.handle_brainflow_error("test_get_data_without_start_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            
    def test_operation_order_change(self):
        logger.info('test_concurrent_operation_order_change')
        try:
            self.board_shim.start_stream()
            self.board_shim.prepare_session()
        except BrainFlowError as e:
            if e.exit_code == brainflow.BrainFlowExitCodes.BOARD_NOT_CREATED_ERROR:  # 根据实际的错误类型判断是否是超时异常
                logger.info("test_concurrent_operation_order_change: 并发操作顺序变化验证通过")
            else:
                self.handle_brainflow_error("test_concurrent_operation_order_change", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_operation_order_change", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
    
    def handle_brainflow_error(self, test_method_name, error):
        """
        处理BrainFlowError异常的公共方法，可根据需要进一步细化错误处理逻辑
        """
        logger.error(f"{test_method_name}: 脑flow业务异常,信息: {error}")
        self.fail(f"在{test_method_name}中出现脑flow业务异常: {error}")

    def handle_general_exception(self, test_method_name, error):
        """
        处理其他通用异常的公共方法，可根据需要进一步细化错误处理逻辑
        """
        logger.error(f"{test_method_name}: 其他运行时异常，信息: {error}")
        self.fail(f"在{test_method_name}中出现其他运行时异常: {error}")
        
    @unittest.skipIf(is_skip_concurrent(),'just skip concurrent')
    def test_concurrent_prepare_session(self):
        logger.info('test_concurrent_prepare_session')
        try:
            self.board_shim.prepare_session()
            self.board_shim2.prepare_session()
            eeg_channels = self.board_shim.get_eeg_channels(self.board_id)
            self.assertGreaterEqual(len(eeg_channels), self.CHANNEL_NUM)
            self.assertEqual(self.board_shim.is_prepared(), True)
            eeg_channels2 = self.board_shim.get_eeg_channels(self.board_id2)
            self.assertGreaterEqual(len(eeg_channels2), self.CHANNEL_NUM2)
            self.assertEqual(self.board_shim2.is_prepared(), True)
            logger.info("test_concurrent_prepare_session: 会话准备成功，脑电通道数量及其他验证通过")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_prepare_session", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_prepare_session", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()
            
    @unittest.skipIf(is_skip_concurrent(),'just skip concurrent')
    def test_concurrent_release_session(self):
        logger.info('test_concurrent_release_session')
        try:
            self.prepare_session(self.board_shim)
            self.release_board_shim(self.board_shim)
            self.prepare_session(self.board_shim2)
            self.release_board_shim(self.board_shim2)
            self.assertEqual(self.board_shim.is_prepared(), False)
            self.assertEqual(self.board_shim2.is_prepared(), False)
            logger.info("test_concurrent_release_session: 会话释放成功")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_release_session", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_release_session", e)
            
    @unittest.skipIf(is_skip_concurrent(),'just skip concurrent')
    def test_concurrent_start_stream(self):
        logger.info('test_concurrent_start_stream')
        try:
            self.prepare_session(self.board_shim)
            self.board_shim.start_stream()
            self.prepare_session(self.board_shim2)
            self.board_shim2.start_stream()
            data = self.board_shim.get_board_data()
            self.assertEqual(len(data), self.board_shim.get_num_rows(board_id=self.board_id))
            data2 = self.board_shim2.get_board_data()
            self.assertEqual(len(data2), self.board_shim2.get_num_rows(board_id=self.board_id2))
            logger.info("test_concurrent_start_stream: 流启动成功，数据验证通过")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_start_stream", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_start_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.stop_stream()
                self.board_shim2.release_session()

    @unittest.skipIf(is_skip_concurrent(),'just skip concurrent')
    def test_concurrent_stop_stream(self):
        logger.info('test_concurrent_stop_stream')
        try:
            self.prepare_session(self.board_shim)
            self.board_shim.start_stream()
            self.board_shim.stop_stream()
            self.prepare_session(self.board_shim2)
            self.board_shim2.start_stream()
            self.board_shim2.stop_stream()
            data = self.board_shim.get_board_data()
            self.assertNotEqual(len(data), self.board_shim.get_num_rows(board_id=self.board_id))
            data2 = self.board_shim2.get_board_data()
            self.assertNotEqual(len(data2), self.board_shim2.get_num_rows(board_id=self.board_id2))
            logger.info("test_concurrent_stop_stream: 流停止成功，资源释放验证通过")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_stop_stream", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_stop_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()
            
    @unittest.skipIf(is_skip_concurrent(),'just skip concurrent')
    def test_concurrent_get_sampling_rate(self):
        logger.info('test_concurrent_get_sampling_rate')
        try:
            self.prepare_session(self.board_shim)
            sampling_rate = self.board_shim.get_sampling_rate(board_id=self.board_id)
            self.assertEqual(sampling_rate, self.SAMPLING_RATE)
            self.prepare_session(self.board_shim2)
            sampling_rate2 = self.board_shim2.get_sampling_rate(board_id=self.board_id2)
            self.assertEqual(sampling_rate2, self.SAMPLING_RATE2)
            logger.info(f"test_concurrent_get_sampling_rate: 获取采样率成功，采样率为 {sampling_rate}")
        except BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_get_sampling_rate", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_get_sampling_rate", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()

    
def main(aging_duration: float = 0.5):
    """
    主函数，用于执行多轮测试并全面处理测试结果，支持将日志输出到文件或控制台。
    :param aging_duration: 测试持续的时长（单位：小时），默认值为0.5小时
    """

    end_time = time.time() + aging_duration * 3600
    round_num = 0
    total_tests_run = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    total_passed = 0

    while time.time() < end_time:
        round_num += 1
        logger.info(f"开始第 {round_num} 轮测试")
        start_time = time.time()
        test_result = '不通过'

        # 动态创建临时测试类，继承自TestSDKApi并传递必要参数
        TempTestClass = type('TempTest', (TestSDKApi,),{'__init__': lambda self, *args, **kwargs: TestSDKApi.__init__(self,*args, **kwargs)})

        suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        tests = loader.loadTestsFromTestCase(TempTestClass)
        suite.addTests(tests)

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        # 更新每轮测试的统计信息
        total_tests_run += result.testsRun
        total_failures += len(result.failures)
        total_errors += len(result.errors)
        total_skipped += len(result.skipped)
        total_passed += result.testsRun - len(result.failures) - len(result.skipped) - len(result.errors)

        # 处理测试失败情况
        handle_test_result(result.failures, handle_failure_result)

        # 处理测试错误情况
        handle_test_result(result.errors, handle_error_result)

        # 处理测试跳过情况
        handle_test_result(result.skipped, handle_skipped_result)

        # 处理测试成功情况
        if result.wasSuccessful():
            logger.info("All tests passed successfully.\n")
            test_result = '通过'
        else:
            logger.info("Some tests failed or encountered errors.\n")

        end_time2 = time.time()
        elapsed_time = end_time2 - start_time
        logger.info(f"\n\n 执行case: {result.testsRun}, 耗时： {elapsed_time:.3f}s\n")
        # logger.info(f"fail case:{len(result.failures)}条\n")
        # logger.info(f"skip case:{len(result.skipped)}条\n")
        # logger.info(f"error case:{len(result.errors)}条\n")
        # logger.info(f"pass case:{result.testsRun - len(result.failures) - len(result.skipped) - len(result.errors)}条\n")

        logger.info(f"#################第 {round_num} 轮测试结束，测试结果：{test_result}#############\n")

    # 输出整个测试过程的汇总统计信息
    logger.info(f"========== 全部 {round_num} 轮测试结束，汇总统计信息如下 ==========")
    logger.info(f"总执行测试用例数: {total_tests_run}")
    logger.info(f"总失败用例数: {total_failures}")
    logger.info(f"总错误用例数: {total_errors}")
    logger.info(f"总跳过用例数: {total_skipped}")
    logger.info(f"总通过用例数: {total_passed}")


def handle_test_result(test_result_list, handler_func):
    """
    通用的处理测试结果的函数，根据不同的结果类型调用相应的处理函数。

    :param test_result_list: 包含测试结果信息的列表，每个元素包含测试方法名和对应的消息（失败、错误、跳过的原因等）
    :param handler_func: 具体处理对应结果的函数，如处理失败的函数、处理错误的函数等
    """
    for test_method_name, message in test_result_list:
        handler_func(test_method_name, message)


def handle_failure_result(test_method_name, failure_message):
    """
    处理测试方法失败的情况，记录详细的失败信息到日志，并尝试提取关键的错误信息（可根据实际情况优化）。

    :param test_method_name: 失败的测试方法名称
    :param failure_message: 失败的详细信息
    """
    try:
        # 尝试从详细的失败信息中提取关键部分（这里假设是简单的字符串处理，可根据实际错误格式调整）
        key_error_info = failure_message.splitlines()[0] if failure_message else ""
        logger.error(f"测试方法 {test_method_name} 失败，关键错误信息: {key_error_info}")
    except IndexError:
        logger.error(f"测试方法 {test_method_name} 失败，无法解析关键错误信息")


def handle_error_result(test_method_name, error_message):
    """
    处理测试方法出现错误的情况，记录详细的错误信息到日志，并尝试提取关键的错误原因（可根据实际情况优化）。

    :param test_method_name: 出现错误的测试方法名称
    :param error_message: 错误的详细信息
    """
    try:
        # 尝试从详细的错误信息中提取关键部分（这里假设是简单的字符串处理，可根据实际错误格式调整）
        key_error_info = error_message.splitlines()[0] if error_message else ""
        logger.error(f"测试方法 {test_method_name} 出现错误，关键错误原因: {key_error_info}")
    except IndexError:
        logger.error(f"测试方法 {test_method_name} 出现错误，无法解析关键错误原因")


def handle_skipped_result(test_method_name, reason):
    """
    处理测试方法被跳过的情况，记录被跳过的原因到日志。

    :param test_method_name: 被跳过的测试方法名称
    :param reason: 被跳过的原因
    """
    logger.info(f"测试方法 {test_method_name} 被跳过，原因: {reason}")


def handle_successful_result():
    logger.info("所有测试成功执行完毕")

if __name__ == '__main__':
    aging_duration = 0.00001
    main(aging_duration=aging_duration)