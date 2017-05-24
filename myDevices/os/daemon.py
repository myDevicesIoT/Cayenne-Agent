#!/usr/bin/env python
from sys import exit
from datetime import datetime
from os.path import getmtime
from myDevices.utils.logger import exception, info, warn, error, debug
from myDevices.os.services import ServiceManager

#defining reset timeout in seconds
RESET_TIMEOUT=30
FAILURE_COUNT=1000
PYTHON_BIN='/usr/bin/python3'
failureCount={}
startFailure={}
errorList= (-3, -2, 12, 9, 24)
class Daemon:
	def OnFailure(component, error=0):
		#-3=Temporary failure in name resolution
		info('Daemon failure handling ' + str(error))
		if error in errorList:
			Daemon.Restart()
		if component not in failureCount:
			Daemon.Reset(component)
		failureCount[component]+=1
		now = datetime.now()
		if startFailure[component]==0:
			startFailure[component]=now
		elapsedTime=now-startFailure[component]
		if (elapsedTime.total_seconds() >= RESET_TIMEOUT) or ( failureCount[component] > FAILURE_COUNT):
			warn('Daemon::OnFailure myDevices is going to restart after ' +str(component) + ' failed: ' + str(elapsedTime.total_seconds()) + ' seconds and ' + str(failureCount) + ' times')
			Daemon.Restart()
	def Reset(component):
		startFailure[component]=0
		failureCount[component]=0
	def Restart():
		try:
			info('Daemon Restarting myDevices' )
			(output, returncode) = ServiceManager.ExecuteCommand('sudo service myDevices restart')
			debug(str(output) + ' ' + str(returncode))
			del output
		except:
			exception ("Daemon::Restart Unexpected error")
			Daemon.Exit()
	def Exit():
		info('Critical failure. Closing myDevices process...')
		exit('Daemon::Exit Closing agent. Critical failure.')




