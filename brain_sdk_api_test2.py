import logging
import threading
import time
import unittest

from brainflow import BoardIds, BoardShim, BrainFlowError
import brainflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


import unittest
import logging
import brainflow
from brainflow.board_shim import BoardShim, BrainFlowError
import time
import psutil  # 用于获取系统资源信息，如内存占用情况

# 设置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestSDKApi(unittest.TestCase):
    def __init__(self, mac_address: str,mac_address2: str, board_id: int,board_id2: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_address = mac_address
        self.mac_address2 = mac_address2
        self.board_id = board_id
        self.board_id2 = board_id2
        self.timeout = 10
        # 以下为测试常数定义部分
        self.CHANNEL_NUM = 2  # 不同产品的通道数目有区分，这里假设真实值是7
        self.CHANNEL_NUM2 = 7
        self.SAMPLING_RATE = 250  # 根据产品定义的实际采样率，假设真实值是250

    def setUp(self):
        logger.info('setUp')
        params = brainflow.BrainFlowInputParams()
        params.mac_address = self.mac_address
        params.timeout = self.timeout
        self.board_shim = BoardShim(self.board_id, params)
        params2 = brainflow.BrainFlowInputParams()
        params2.mac_address = self.mac_address2
        params2.timeout = self.timeout
        self.board_shim2 = BoardShim(self.board_id2, params2)

    def tearDown(self):
        logger.info('tearDown')
        if self.board_shim is not None:
            self.board_shim = None
        if self.board_shim2 is not None:
            self.board_shim2 = None

    def test_prepare_session(self):
        logger.info('test_prepare_session')
        try:
            self.board_shim.prepare_session()
            
            eeg_channels = self.board_shim.get_eeg_channels(self.board_id)
            self.assertGreaterEqual(len(eeg_channels), self.CHANNEL_NUM)
            
            self.assertEqual(self.board_shim.is_prepared(), True)
            
            logger.info("test_prepare_session: 会话准备成功，脑电通道数量及其他验证通过")
            
        except BrainFlowError as e:
            logger.error(f"test_prepare_session: 其他脑flow业务异常,信息: {e}")
            self.fail(f"在test_prepare_session中出现其他脑flow业务异常: {e}")
            
        except Exception as e:
            logger.error(f"test_prepare_session: 其他运行时异常，信息: {e}")
            self.fail(f"在test_prepare_session中出现其他运行时异常: {e}")
            
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
            logger.error(f"在test_start_stream中出现脑flow业务异常: {e}")
            self.fail(f"在test_start_stream中出现脑flow业务异常: {e}")
            
        except Exception as e:
            logger.error(f"在test_start_stream中出现其他运行时异常: {e}")
            self.fail(f"在test_start_stream中出现其他运行时异常: {e}")
            
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()

    # def test_concurrent_start_stream(self):
    #     try:
    #         self.board_shim.prepare_session()

    #         def start_stream_thread():
    #             self.board_shim.start_stream()
    #             data = self.board_shim.get_board_data()
    #             self.assertEqual(len(data), self.board_shim.get_num_rows(board_id=self.board_id))
    #             self.board_shim.stop_stream()
    #             self.board_shim.release_session()

    #         threads = []
    #         for _ in range(5):  # 模拟5个并发启动流的线程
    #             t = threading.Thread(target=start_stream_thread)
    #             threads.append(t)
    #             t.start()
    #         for t in threads:
    #             t.join()
    #         logger.info("并发启动流测试成功")
            
    #     except BrainFlowError as e:
    #         logger.error(f"并发启动流出现脑flow业务异常: {e}")
    #         self.fail(f"并发启动流出现脑flow业务异常: {e}")
            
    #     except Exception as e:
    #         logger.error(f"并发启动流出现其他运行时异常: {e}")
    #         self.fail(f"并发启动流出现其他运行时异常: {e}")
    
   

    def test_get_sampling_rate(self):
        logger.info('test_get_sampling_rate')
        try:
            self.board_shim.prepare_session()
            sampling_rate = self.board_shim.get_sampling_rate(board_id=self.board_id)
            self.assertEqual(sampling_rate, self.SAMPLING_RATE)
            logger.info(f"test_get_sampling_rate: 获取采样率成功，采样率为 {sampling_rate}")
            
        except BrainFlowError as e:
            logger.error(f"test_get_sampling_rate: 脑flow业务异常,信息: {e}")
            self.fail(f"在test_get_sampling_rate中出现脑flow业务异常: {e}")
            
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
            logger.info("test_get_board_data: 获取少量板卡数据成功")
            
        except BrainFlowError as e:
            logger.error(f"test_get_board_data: 脑flow业务异常,信息: {e}")
            self.fail(f"在test_get_board_data中出现脑flow业务异常: {e}")
            
        except Exception as e:
            logger.error(f"test_get_board_data: 其他运行时异常，信息: {e}")
            self.fail(f"在test_get_board_data中出现其他运行时异常: {e}")
            
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()

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
            logger.error(f"test_stop_stream: 脑flow业务异常,信息: {e}")
            self.fail(f"在test_stop_stream中出现脑flow业务异常: {e}")
            
        except Exception as e:
            logger.error(f"test_stop_stream: 其他运行时异常，信息: {e}")
            self.fail(f"在test_stop_stream中出现其他运行时异常: {e}")
            
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()

    def test_release_session(self):
        logger.info('test_release_session')
        try:
            self.board_shim.prepare_session()
            self.board_shim.release_session()
            
            self.assertEqual(self.board_shim.is_prepared(),False)
            logger.info("test_release_session: 会话释放成功")
            
        except BrainFlowError as e:
            logger.error(f"test_release_session: 脑flow业务异常,信息: {e}")
            self.fail(f"在test_release_session中出现脑flow业务异常: {e}")
            
        except Exception as e:
            logger.error(f"test_release_session: 其他运行时异常，信息: {e}")
            self.fail(f"在test_release_session中出现其他运行时异常: {e}")
            
        finally:
            pass

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
            logger.error(f"test_concurrent_prepare_session: 其他脑flow业务异常,信息: {e}")
            self.fail(f"test_concurrent_prepare_session: {e}")
            
        except Exception as e:
            logger.error(f"test_concurrent_prepare_session: 其他运行时异常，信息: {e}")
            self.fail(f"在test_concurrent_prepare_session中出现其他运行时异常: {e}")
            
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()
                
    def test_concurrent_release_session(self):
        logger.info('test_concurrent_release_session')
        try:
            self.board_shim.prepare_session()
            self.board_shim.release_session()
            self.board_shim2.prepare_session()
            self.board_shim2.release_session()
            
            self.assertEqual(self.board_shim.is_prepared(),False)
            self.assertEqual(self.board_shim2.is_prepared(),False)
            logger.info("test_concurrent_release_session: 会话释放成功")
            
        except BrainFlowError as e:
            logger.error(f"test_concurrent_release_session: 脑flow业务异常,信息: {e}")
            self.fail(f"在test_concurrent_release_session中出现脑flow业务异常: {e}")
            
        except Exception as e:
            logger.error(f"test_concurrent_release_session: 其他运行时异常，信息: {e}")
            self.fail(f"在test_concurrent_release_session中出现其他运行时异常: {e}")
            
        finally:
            pass
    
    def test_concurrent_release_session(self):
        logger.info('test_concurrent_start_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            self.board_shim2.prepare_session()
            self.board_shim2.start_stream()
            
            data = self.board_shim.get_board_data()
            self.assertEqual(len(data), self.board_shim.get_num_rows(board_id=self.board_id))
            
            data2 = self.board_shim2.get_board_data()
            self.assertEqual(len(data2), self.board_shim2.get_num_rows(board_id=self.board_id2))
            
            logger.info("test_concurrent_release_session: 流启动成功，数据验证通过")
            
        except BrainFlowError as e:
            logger.error(f"在test_concurrent_release_session中出现脑flow业务异常: {e}")
            self.fail(f"在test_concurrent_release_session中出现脑flow业务异常: {e}")
            
        except Exception as e:
            logger.error(f"在test_concurrent_release_session中出现其他运行时异常: {e}")
            self.fail(f"在test_concurrent_release_session中出现其他运行时异常: {e}")
            
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.stop_stream()
                self.board_shim2.release_session()

    def test_concurrent_stop_stream(self):
        logger.info('test_concurrent_stop_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            self.board_shim.stop_stream()
            self.board_shim2.prepare_session()
            self.board_shim2.start_stream()
            self.board_shim2.stop_stream()
            
            data = self.board_shim.get_board_data()
            self.assertNotEqual(len(data), self.board_shim.get_num_rows(board_id=self.board_id))
            data2 = self.board_shim2.get_board_data()
            self.assertNotEqual(len(data2), self.board_shim2.get_num_rows(board_id=self.board_id2))
         
            logger.info("test_concurrent_stop_stream: 流停止成功，资源释放验证通过")
            
        except BrainFlowError as e:
            logger.error(f"test_concurrent_stop_stream: 脑flow业务异常,信息: {e}")
            self.fail(f"在test_concurrent_stop_stream中出现脑flow业务异常: {e}")
            
        except Exception as e:
            logger.error(f"test_concurrent_stop_stream: 其他运行时异常，信息: {e}")
            self.fail(f"在test_concurrent_stop_stream中出现其他运行时异常: {e}")
            
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()
    
    
    def test_concurrent_get_sampling_rate(self):
        logger.info('test_concurrent_get_sampling_rate')
        try:
            self.board_shim.prepare_session()
            sampling_rate = self.board_shim.get_sampling_rate(board_id=self.board_id)
            self.assertEqual(sampling_rate, self.SAMPLING_RATE)
            
            self.board_shim2.prepare_session()
            sampling_rate2 = self.board_shim2.get_sampling_rate(board_id=self.board_id2)
            self.assertEqual(sampling_rate2, self.SAMPLING_RATE)
            logger.info(f"test_concurrent_get_sampling_rate: 获取采样率成功，采样率为 {sampling_rate}")
            
        except BrainFlowError as e:
            logger.error(f"test_concurrent_get_sampling_rate: 脑flow业务异常,信息: {e}")
            self.fail(f"在test_concurrent_get_sampling_rate中出现脑flow业务异常: {e}")
            
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()
    def test_concurrent_get_board_data(self):
        pass
    
    
def main(mac_address: str,mac_address2: str, board_id: int,board_id2: int,aging_duration:float = 0.5):
    end_time = time.time() + aging_duration * 3600
    round_num = 0
    while time.time() < end_time:
        start_time = time.time()
        test_result = '不通过'
        round_num += 1
        TempTestClass = type('TempTest', (TestSDKApi,), {'__init__': lambda self, *args, **kwargs: TestSDKApi.__init__(self, mac_address,mac_address2, board_id,board_id2, *args, **kwargs)})

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

        end_time2 = time.time()
        elapsed_time = end_time2 - start_time
        logger.info(f"\n\n 执行case: {result.testsRun}, 耗时： {elapsed_time:.3f}s\n")
        logger.info(f"#################第 {round_num} 轮测试结束，测试结果：{test_result}#############\n")


def handle_failure_result(test_method_name, failure_message):
    logger.error(f"测试方法 {test_method_name} 失败，失败信息: {failure_message}")


def handle_error_result(test_method_name, error_message):
    logger.error(f"测试方法 {test_method_name} 出现错误，错误信息: {error_message}")


def handle_skipped_result(test_method_name, reason):
    logger.info(f"测试方法 {test_method_name} 被跳过，原因: {reason}")


def handle_successful_result():
    logger.info("所有测试成功执行完毕")


if __name__ == '__main__':
    # mac_address = '60:77:71:74:E6:B7' # C4:64:E3:D8:E6:D2
    board_id = 57
    mac_address = 'C4:64:E3:D8:E6:D2'
    mac_address2 = 'C4:64:E3:D8:E3:EE'
    board_id2 = 58
    aging_duration = 0.00001
    main(mac_address=mac_address,mac_address2=mac_address2, board_id=board_id,board_id2=board_id2,aging_duration=aging_duration)