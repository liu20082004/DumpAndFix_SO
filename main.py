# -*- coding:utf-8 -*-

import subprocess
import os
import socket
import re
import time

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
	pid = 0
	for eachline in buf:
		if '' == eachline:
			continue
		item = eachline.split()
		if appname == item[-1]:
			pid = item[1]
			break
	return pid

def getSOAddrByName(SOName,buf):
	buf = buf.split('\r\n')
	addrs = []
	for eachline in buf:
		if '' == eachline:
			continue
		item = eachline.split()
		if SOName in item[-1]:
			addr = item[0].split('-')
			for i in addr:
				addrs.append(i)
	addrStart = int(addrs[0],16)
	addrEnd = int(addrs[-1],16)
	size = addrEnd - addrStart
	return addrStart,size

def main():
	#appName = 'com.obdstar.x300dp'
	appNames = ['com.obdstar.x300dp', 'com.xtooltech.PS60', 'com.xtooltech.i80PAD']

	adbServer('')
	adbServer('su')
	recvbuf = adbServer('ps')

	for appName in appNames:
		pid = findPIDFromAppname(appName,recvbuf)
		if 0 != pid:
			break
	if 0 == pid :
		print 'Can find any apps!'
		return

	#获取目标内存地址
	strGetMem = 'cat /proc/%s/maps' %(pid)

	recvbuf = adbServer(strGetMem)
	#print recvbuf

	bassAddr,size = getSOAddrByName('libscan.so',recvbuf)
	#bassAddr, size = getSOAddrByName('Diag.so', recvbuf)
	print bassAddr,size

	#strDD = 'dd if=/proc/%s/mem of=/sdcard/dump.so skip=%s ibs=1 count=%s' %(pid,bassAddr,size)
	strDD = 'dd if=/proc/%s/mem of=/sdcard/dump.so skip=%s ibs=1 count=%s' % (pid, bassAddr, size)
	print strDD
	#recvbuf = adbServer(strDD)

	s = adbConnect()
	adbshellCMD(s, strDD)
	time.sleep(20)
	recv = adbshellRecv(s)
	print recv
	s.close()
	time.sleep(5)

	s = adbConnect()
	req_msg = 'sync:/sdcard/dump.so d:\\'
	s.sendall('%04x' % (len(req_msg)))
	s.sendall(req_msg)

	i=0
	newbuf=''
	while i<20:
		buf = adbshellRecv(s)
		newbuf = newbuf+buf
		i=i+1

	#time.sleep(30)
	#newbuf = adbshellRecv(s)
	print newbuf

if __name__ == '__main__' :
	main()
	print 'Program Finish'
