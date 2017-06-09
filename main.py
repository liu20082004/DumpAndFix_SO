# -*- coding:utf-8 -*-

import subprocess
import os
import socket
import re
import time
import ADB_SHELL

def adbConnect():
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	s.settimeout(10)
	while True :
		try :
			s.connect(('127.0.0.1',5037))
		except :
			os.system('adb start-server')
			continue
		else :
			break
	req_msg = 'host:transport-any'
	s.sendall('%04x' %(len(req_msg)))
	s.sendall(req_msg)
	resp = s.recv(4)
	if 'OKAY'!=resp :
		s = None
	return s

def adbshellCMD(socket,CMD) :
	req_msg = 'shell:%s' %(CMD)
	socket.sendall('%04x' %(len(req_msg)))
	socket.sendall(req_msg)

def adbshellRecv(socket) :
	result = socket.recv(4)
	if 'OKAY'!=result :
		return None
	else:
		buf='' #以字符串的形式呈现
		while True :
			try :
				resp = socket.recv(4096)
			except :
				break
			else:
				if 0 == len(resp):  # recv函数返回值为字符串,只能通过判断字符串长度来确定是否有数据接收
					break
				else:
					#buf.append(resp)
					buf += resp
		return buf

def findPIDFromCOMMAND( command , data ) :
	bufs = []
	for buf in data : #这个循环处理ps得到的数据
		#print str
		if ''!=buf :
			psTab = {}
			str = buf.split()
			psTab['PID'] = str[0]
			psTab['USER'] = str[1]
			psTab['TIME'] = str[2]
			psTab['COMMAND'] = ''
			for i in range(3,len(str)) :
				psTab['COMMAND'] += str[i] + ' '
			#print psTab
			bufs.append(psTab)
	result = []
	for item in bufs :
		if command in item['COMMAND'] :
			result.append( item )
	return result

def adbServer(command):
	s = adbConnect()
	adbshellCMD(s, command)
	recv = adbshellRecv(s)
	return recv

def findPIDFromAppname(appname,buf):
	buf = buf.split('\r\n')
	# 走简易方法(强行按这种格式来划分): USER     PID   PPID  VSIZE RSS   %sWCHAN    PC         NAME\n
	# 发现简易方法行不通啊,因为每个系统,对ps指令回复是不一样的,不能一概而论
	position = 0xff
	if 'PID' in buf[0]:
		position = buf[0].split().index('PID')
	pid = 0
	for eachline in buf:
		if '' == eachline:
			continue
		item = eachline.split()
		if appname == item[-1]:
			pid = item[position]
			break
	return pid

def getSOAddrByName(SOName,buf):
	buf = buf.split('\r\n')
	addrs = []
	for eachline in buf:
		if '' == eachline:
			continue
		if -1 != eachline.find(SOName) :
			item = eachline.split()
			addr = item[0].split('-')
			for i in addr:
				addrs.append(i)
	if addrs == []:  # 当地址为空的时候,提示找不到目标动态库
		return 0,0
	else:
		addrStart = int(addrs[0],16)
		addrEnd = int(addrs[-1],16)
		size = addrEnd - addrStart
		return addrStart,size

def main111():
	"""
	unknown option -- c
	Usage: su [options] [args...]
	Options:
		-c, --command COMMAND         pass COMMAND to the invoked shell
		-cn, --context CONTEXT        switch to SELinux CONTEXT before invoking
		-d, -ad, --daemon, --auto-daemon
					start the su daemon
		-i, --install                 check and repair su files
		-h, --help                    display this help message and exit
		-v, -V, --version             display version number and exit
	Usage#2: su uid COMMAND...
	"""

	appNames = ['com.obdstar.x300dp', 'com.xtooltech.PS60', 'com.xtooltech.i80PAD']

	adbServer('')
	a = adbServer('su')
	print a
	recvbuf = adbServer('su -c ps')

	for appName in appNames:
		pid = findPIDFromAppname(appName,recvbuf)
		if 0 != pid:
			break
	if 0 == pid :
		print 'Can find any apps!'
		return

	 #获取目标内存地址
	strGetMem = 'su -c ' + 'cat /proc/%s/maps' %(pid)

	recvbuf = adbServer(strGetMem)
	# print recvbuf

	if appName == 'com.obdstar.x300dp':
		bassAddr, size = getSOAddrByName('Diag.so', recvbuf)
	else:
		bassAddr, size = getSOAddrByName('libscan.so', recvbuf)
	print bassAddr,size

	# strDD = 'dd if=/proc/%s/mem of=/sdcard/dump.so skip=%s ibs=1 count=%s' %(pid,bassAddr,size)
	strDD = 'su -c dd if=/proc/%s/mem of=/sdcard/dump.so skip=%s ibs=1 count=%s' % (pid, bassAddr, size)
	print strDD
	#recvbuf = adbServer(strDD)

	s = adbConnect()
	adbshellCMD(s, strDD)
	time.sleep(20)
	recv = adbshellRecv(s)
	print recv
	s.close()
	time.sleep(5)

	# 偷懒了就直接用系统调用adb的pull命令把文件传上来
	adb_pull = subprocess.Popen(['adb','pull','/sdcard/dump.so','d:\\'])
	adb_pull.wait()
	#print adb_pull.stdout

def main():
	app_names = ['com.obdstar.x300dp', 'com.xtooltech.PS60', 'com.xtooltech.i80PAD']
	my_adbshell_server = ADB_SHELL.adbShell()

	print 'open adb shell'
	result, recvbuf = my_adbshell_server.adb_server('')
	if 1 == result:
		print recvbuf
		return

	print 'switch to super user'
	result, recvbuf = my_adbshell_server.adb_server('su')
	if 1 == result:
		print recvbuf
		return

	print 'get list of apps'
	result, recvbuf = my_adbshell_server.adb_server('su -c ps')
	if 1 == result:
		print recvbuf
		return
	else:
		print 'search for target~s pid'
		for appname in app_names:
			pid = findPIDFromAppname(appname, recvbuf)
			if 0 != pid:
				break
		if 0 == pid :
			print 'Can find any apps!'
			return

	print 'get target~s memory'
	 #获取目标内存地址
	strGetMem = 'su -c ' + 'cat /proc/%s/maps' %(pid)
	result, recvbuf = my_adbshell_server.adb_server(strGetMem)
	if 1 == result:
		print recvbuf
		return
	else:
		print 'search for the address and size of target~s sofile'
		if appname == 'com.obdstar.x300dp':
			bassAddr, size = getSOAddrByName('Diag.so', recvbuf)
		else:
			bassAddr, size = getSOAddrByName('libscan.so', recvbuf)
		if (0 == bassAddr) and (0 == size):
			print 'can found the sofile'
			return

	print 'dump!'
	# strDD = 'dd if=/proc/%s/mem of=/sdcard/dump.so skip=%s ibs=1 count=%s' %(pid,bassAddr,size)
	strDD = 'su -c dd if=/proc/%s/mem of=/sdcard/dump.so skip=%s ibs=1 count=%s' % (pid, bassAddr, size)
	s = adbConnect()
	adbshellCMD(s, strDD)
	time.sleep(20)
	recv = adbshellRecv(s)
	print recv
	s.close()
	time.sleep(5)

	print u'adb pull to d:\\'
	# 偷懒了就直接用系统调用adb的pull命令把文件传上来
	try:
		adb_pull = subprocess.Popen(['adb','pull','/sdcard/dump.so','d:\\'])
		adb_pull.wait()
	except IOError, e:
		print e
		return
	except e:
		print e
		return


if __name__ == '__main__' :
	main()
	print 'Program Finish'
