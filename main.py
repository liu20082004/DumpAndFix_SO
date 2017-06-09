# -*- coding:utf-8 -*-

import subprocess
import os
import socket
import re
import time
import ADB_SHELL


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


def get_target_info():
	"""从配置文件中获取目标app信息"""
	target_info = []
	try:
		targetfile = open('target.ini', 'r')
		data = targetfile.readlines()
		targetfile.close()
	except IOError, e:
		return 1, e
	for eachline in data:
		target_info.append(eachline.strip().split('\t'))
	return 0, target_info


def main():

	"""
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

	# 从配置文件中获取目标信息
	result, target_info = get_target_info()
	# 实例化adbshell
	my_adbshell_server = ADB_SHELL.adbShell()

	print '>>>>open adb shell'
	result, recvbuf = my_adbshell_server.adb_server('')
	if 1 == result:
		print recvbuf
		return

	print '>>>>switch to super user'
	result, recvbuf = my_adbshell_server.adb_server('su')
	if 1 == result:
		print recvbuf
		return

	print '>>>>get list of apps'
	result, recvbuf = my_adbshell_server.adb_server('su -c ps')
	if 1 == result:
		print recvbuf
		return
	else:
		print '>>>>search for target~s pid'
		for target in target_info:
			pid = findPIDFromAppname(target[0], recvbuf)
			if 0 != pid:
				break
		if 0 == pid :
			print '    Can find any apps!'
			return
		print '    %s is found!' %(target[0])

	print '>>>>get target~s memory'
	 #获取目标内存地址
	strGetMem = 'su -c ' + 'cat /proc/%s/maps' %(pid)
	result, recvbuf = my_adbshell_server.adb_server(strGetMem)
	if 1 == result:
		print recvbuf
		return
	else:
		print '>>>>search for the address and size of %s' %(target[1])
		bassAddr, size = getSOAddrByName(target[1], recvbuf)
		if (0 == bassAddr) and (0 == size):
			print '    can found the sofile'
			return
		print '    %s~s address = %d\n    %s~s size = %d' %(target[1], bassAddr, target[1], size)

	print '>>>>dump!'
	strDD = 'su -c dd if=/proc/%s/mem of=/sdcard/dump.so skip=%s ibs=1 count=%s' % (pid, bassAddr, size)
	result, recvbuf = my_adbshell_server.adb_server(strDD)
	if 1 == result:
		print recvbuf
		return
	print recvbuf
	# 通过20s的延时来等待DD指令的完成
	#time.sleep(20)

	print u'>>>>adb pull to d:\\'
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
