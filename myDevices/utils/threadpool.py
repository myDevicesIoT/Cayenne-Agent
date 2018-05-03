"""
This module provides a singleton thread pool class
"""
from concurrent.futures import ThreadPoolExecutor
from myDevices.utils.singleton import Singleton

executor = ThreadPoolExecutor(max_workers=4)
class ThreadPool(Singleton):
    """Singleton thread pool class"""

    @staticmethod
    def Submit(func):
        """Submit a function for the thread pool to run"""
        executor.submit(func)

    @staticmethod
    def Shutdown():
        """Shutdown the thread pool"""
        executor.shutdown()
        