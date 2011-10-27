# Marantz Serial Interface
# RS232 control of Marantz Amplifiers

import serial
import platform 
import time
import thread
import copy
import ConfigParser
from threading import *
from datetime import datetime
from collections import deque

class AmpStatus:
	pwr = False
	vol = -9999
	src = 'XX'
	mute = False
	att = False
	bass = -9999
	treble = -9999
	dataOK = False
	
	def show(self):
		if self.dataOK == True:
			print '---- AMP STATUS ----'
			print 'Power     = ' + str(self.pwr)
			print 'Volume    = ' + str(self.vol)
			print 'Source    = ' + str(self.src)
			print 'Mute      = ' + str(self.mute)
			print 'Attenuate = ' + str(self.att)
			print 'Bass      = ' + str(self.bass)
			print 'Treble    = ' + str(self.treble)
			print '--------------------'		
		else:
			print '+--- AMP STATUS ---+'
			print '|     No Data      |'
			print '+------------------+'

knownSources = []

class CmdType:

	cmd = ''
	value = ''

def readConfig():
	global knownSources
	print 'MSI: Attempting to load a config...'
	parser = ConfigParser.SafeConfigParser()
	parser.read("./receiverConfigs/marantz7500.cfg")
	
	section_names = parser.sections() # returns a list of strings of section names
	
	for section in section_names:
		print section
		if (section == "sources"):
			for source_name, source_value in parser.items(section):
				print source_name.upper() + " : " + source_value.upper()
				knownSources.append((source_name.upper(), source_value.upper()))


class MarantzSerialInterface(Thread):

	def __init__(self, ser):
		Thread.__init__(self)
		self.serialPort = ser
		
		self.ampStatus = AmpStatus()
		self.statusLock = Condition()
		
		self.cmdQueue = deque([])
		self.cmdQueueLock = Condition()

	def __refreshStatus__(self):
		if self.__getStatus__('PWR') == '2':
			self.ampStatus.pwr = True
			self.ampStatus.dataOK = True
		else:
			self.ampStatus.dataOK = False
			return
		
		self.ampStatus.vol = int(self.__getStatus__('VOL'))
		
		src = self.__getStatus__('SRC')
		self.ampStatus.src = src
		# If the Source is only one character long, we know we're in a bad data state. (i.e. the Receiver is booting up)
		if len(src) <> 2:
			self.ampStatus.dataOK = False
			return	
			
		if self.__getStatus__('AMT') == '2':
			self.ampStatus.mute = True
		else:
			self.ampStatus.mute = False
			
		if self.__getStatus__('ATT') == '2':
			self.ampStatus.att = True
		else:
			self.ampStatus.att = False
			
		self.ampStatus.bass = int(self.__getStatus__('TOB'))
		self.ampStatus.treble = int(self.__getStatus__('TOT'))

	
	def __readReturn__(self, timeout = 1.0):
		buffer = ''
		startTime = datetime.now()
		while buffer.find('\r') == -1:
			buffer = buffer + self.serialPort.read()
			if (datetime.now() - startTime).microseconds / 100000.0 > timeout:
				return 'ERROR'
		endTime = datetime.now()
		#print 'Command executed in (secs) ' + str((endTime - startTime).microseconds / 100000.0)
		return buffer

	
	def __sendCmd__(self, cmdCode, cmdValue):
		
		cmd = '@' + cmdCode + ':' + cmdValue + '\r'
		print 'Sending command: ' + cmd
		self.serialPort.write(cmd)
		ack = self.__readReturn__(5)
		print 'Got back: ' + cmd
		if ack == cmd:
			return True
		if ack == 'ACK\r':
			return True
		if ack == 'ERROR':
			print 'ERROR: Command not executed'
			return False	
		ack.strip('\r')
		vals = ack.split(':');
		if vals[0] == ('@' + cmdCode):
			return True
		print 'ERROR: Command not executed'
		return False

	
	def __getStatus__(self, statusCmd):
		#print 'Getting Status: ' + statusCmd
		cmd = '@' + statusCmd + ':?\r'
		self.serialPort.write(cmd)
		ack = self.__readReturn__()
		if ack == 'ERROR':
			return 'ERROR'
		print 'Serial Response: ' + ack
		ack = ack.rstrip()
		vals = ack.split(':');
		print 'Status ' + statusCmd + ' = ' + vals[1]
		return "" + vals[1]
	
	
	def __setAutoStatus__(self, switch):
		if switch == True:
			self.__sendCmd__('AST','9')
		else:
			self.__sendCmd__('AST','0')

	
	def __processStatus__(self, statusStr):
		statusStr = statusStr.rstrip()
		vals = statusStr.split(':');
		if vals[0] == '@PWR':
			if vals[1] == '2':
				self.ampStatus.pwr = True
			else:
				self.ampStatus.pwr = False
			return True
		if vals[0] == '@VOL':
			self.ampStatus.vol = int(vals[1])
			return True	
		if vals[0] == '@SRC':
			self.ampStatus.src = "" + vals[1]
			return True	
		if vals[0] == '@AMT':
			if vals[1] == '2':
				self.ampStatus.mute = True
			else:
				self.ampStatus.mute = False
			return True	
		if vals[0] == '@ATT':
			if vals[1] == '2':
				self.ampStatus.att = True
			else:
				ampStatus.att = False
			return True	
		if vals[0] == '@TOB':
			self.ampStatus.bass = int(vals[1])
			return True	
		if vals[0] == '@TOT':
			self.ampStatus.treble = int(vals[1])
			return True
		return False

	
	def __autoListenOnce__(self):
		ack = self.__readReturn__()
		if ack == 'ERROR':
			return
		if ack.find('OSD') != -1:
			return
		return self.__processStatus__(ack)


	# Main thread function.
	def cmd(self, cmd, value):
		tcmd = CmdType()
		tcmd.cmd = cmd
		tcmd.value = value
		self.cmdQueueLock.acquire()
		self.cmdQueue.append(tcmd)
		self.cmdQueueLock.release()
		
	def cmdMeta(self, cmdString):
		if cmdString == 'powerOn':
			self.cmd('PWR', '2')	
		if cmdString == 'powerOff':
			self.cmd('PWR', '1')
		if cmdString == 'muteOn':
			self.cmd('AMT', '2')	
		if cmdString == 'muteOff':
			self.cmd('AMT', '1')	
		if cmdString == 'volumeUp':
			self.cmd('VOL', '1')
		if cmdString == 'volumeDown':
			self.cmd('VOL', '2')
		if cmdString == 'bassUp':
			self.cmd('TOB', '1')
		if cmdString == 'bassDown':
			self.cmd('TOB', '2')
		if cmdString == 'trebleUp':
			self.cmd('TOT', '1')
		if cmdString == 'trebleDown':
			self.cmd('TOT', '2')
		
	def status(self):
		self.statusLock.acquire()
		outStatus = copy.deepcopy(self.ampStatus)
		self.statusLock.release()
		return outStatus
		
	def sources(self):
		return knownSources

	def run(self):
		print "Turning AutoStatus On"
		self.__setAutoStatus__(True)
		
		self.__refreshStatus__()
	
		exit = False
		while exit == False:
		
			# If we haven't got a good set of status data, go grab some.
			if self.ampStatus.dataOK == False:
				try:
					self.__refreshStatus__()
					if self.ampStatus.dataOK:
						self.ampStatus.show()
				except:
					print "Hit an error."
			# If there is commands in the command queue, execute them
			if len(self.cmdQueue) > 0:
				try:
					self.cmdQueueLock.acquire()
					q = self.cmdQueue.popleft();
					self.cmdQueueLock.release()
					self.__sendCmd__(q.cmd, q.value)
					self.__refreshStatus__()
				except:
					print "Hit an error."
					
			# Listen for auto events coming back from the Amp.
			try:
				gotEvent = self.__autoListenOnce__()
				if gotEvent:
					self.ampStatus.show()
				time.sleep(0.01)
			except:
				print "Hit an error."

print "Starting Marantz Serial Interface"
print 'MSI: Python Version   : ' + platform.python_version()
print 'MSI: PySerial Version : ' + serial.VERSION
readConfig()


	
if __name__ == "__main__":
	
	serialIn = serial.Serial('/dev/ttyS0', 9600, bytesize=8, parity='N', stopbits=1, timeout=0)
	print 'MSI: Connection success - Port: ' + serialIn.portstr

	msi = MarantzSerialInterface(serialIn)
	msi.start()
	
	msi.cmd('PWR', '2')
	
	print "Threads started"
	
	exit = False
	while exit == False:
		raw_input("Press ENTER to refresh Status:\n")
		status = msi.status()
		status.show()
