from  concurrent.futures import ThreadPoolExecutor
from myDevices.utils.singleton import Singleton
import inspect

executor = ThreadPoolExecutor(max_workers=4)
class ThreadPool(Singleton):
	def Submit(something):
		future = executor.submit(something)
	def SubmitParam(*arg):
		executor.submit(*arg)
	def Shutdown():
		executor.shutdown()