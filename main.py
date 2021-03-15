# -*- coding:utf-8 -*-

import subprocess
import os
import socket
import re
import time
import ADB_SHELL
import Fix_SO

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
	addr_start = 0
	addr_end = 0
	flag_next = False
	flag_start = False
	for eachline in buf:
		item = eachline.split()
		if -1 != eachline.find(SOName):
			#item = eachline.split()
			if not flag_start:  # 第一次找到
				addr_start = item[0].split('-')[0]
				flag_start = True
				flag_next = True
			else:
				addr_end = item[0].split('-')[1]
		elif "" == eachline:
			continue
		elif '0' == item[-1] and flag_next:  # 中间存在空行的情况
			addr_end = item[0].split('-')[1]
		else:
			flag_next = False

	if not addr_start or not addr_end:  # 当地址为空的时候,提示找不到目标动态库
		return 0, 0
	else:
		addrStart = int(addr_start, 16)
		addrEnd = int(addr_end, 16)
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

def fix_sofile(file_in, file_out, address_base):
	pass


def DumpData(adb_shell, user, pid, skip, count, outFile):
	"""拷贝数据,成功返回0"""
	cmd_DD = "%s dd if=/proc/%s/mem of=/sdcard/%s skip=%s ibs=1 count=%s" % (user, pid, outFile, skip, count)
	result, recvbuf = adb_shell.adb_server(cmd_DD)
	if 1 == result:
		print recvbuf
	return result


def PullFile(source, dest):
	"""pull到PC"""
	try:
		adb_pull = subprocess.Popen(['adb', 'pull', source, dest])
		adb_pull.wait()
		return 0
	except IOError, e:
		print e
		return 1



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
	elif 'root' in recvbuf:
		str_sysuser = ''
	else:
		str_sysuser = 'su -c '
		print '>>>>switch to super user'
		result, recvbuf = my_adbshell_server.adb_server('su')
		if 1 == result:
			return

	cmd_ps = str_sysuser + 'ps'
	cmd_cat = str_sysuser + 'cat /proc/%s/maps'
	# cmd_DD = str_sysuser + 'dd if=/proc/%s/mem of=/sdcard/dump.so skip=%s ibs=1 count=%s'
	# cmd_DD_sub = str_sysuser + 'dd if=/proc/%s/mem of=/sdcard/temp%d.so skip=%s ibs=1 count=%s'

	print '>>>>get list of apps'
	result, recvbuf = my_adbshell_server.adb_server(cmd_ps)
	if 1 == result:
		print recvbuf
		return
	else:
		print recvbuf
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
	strGetMem = cmd_cat %(pid)
	result, recvbuf = my_adbshell_server.adb_server(strGetMem)
	if 1 == result:
		print recvbuf
		return
	else:
		print '>>>>search for the address and size of %s' %(target[1])

		try:
			f = open('a.txt','w')
			f.write(recvbuf)
			f.close()
		except IOError, e:
			print e

		base_address, size = getSOAddrByName(target[1], recvbuf)
		if (0 == base_address) and (0 == size):
			print '    can found the sofile'
			return
		print '    %s~s address = %d (0x%X)\n    %s~s size = %d (0x%X)' %(target[1], base_address, base_address, target[1], size, size)

	print '>>>>dump!'
	countOfFile = size / 0x100000  # 按照1M来划分
	modOfFile = size % 0x100000
	dump_data = ""
	curdir = os.getcwd()  # 获取当前目录
	tempFileName = "temp.so"
	pull_file_name = "/sdcard/" + tempFileName
	curPCFileName = curdir + "\\" + tempFileName
	count = 0
	for i in range(0, countOfFile):
		if not DumpData(my_adbshell_server, str_sysuser, pid, base_address+i*0x100000, 0x100000, tempFileName) and not PullFile(pull_file_name, curdir):
			with open(curPCFileName, "rb") as tempFile:
				dump_data += tempFile.read()
			count += 1
			os.remove(tempFileName)
			my_adbshell_server.adb_server("rm -r " + pull_file_name)
			continue
		else:
			print("Dump Error")
			return 0

	if modOfFile:
		if not DumpData(my_adbshell_server, str_sysuser, pid, base_address+count*0x100000, modOfFile, tempFileName) and not PullFile(pull_file_name, curdir):
			with open(curPCFileName, "rb") as tempFile:
				dump_data += tempFile.read()
			os.remove(tempFileName)
			my_adbshell_server.adb_server("rm -r " + pull_file_name)
		else:
			print("Dump Error")
			return 0

	# 合并
	if dump_data:
		with open(curdir + '\\dump.so', "wb") as dumpFile:
			dumpFile.write(dump_data)

	size_of_dump = os.path.getsize(curdir + '\\dump.so')
	if size != size_of_dump:
		print 'dump fail'
		#return
		print '>>>>try to fixxing dump.so to fix_dump.so'  # 发现DD出来的数据小于size的情况,莫名其妙...
	else:
		print '>>>>fixxing dump.so to fix_dump.so'
	str_fixfile = curdir + '\\fix_%08X.so' %base_address
	result = Fix_SO.fix_sofile(curdir + '\\dump.so', str_fixfile, base_address)
	if 0 == result:
		print 'Program finish'
	else:
		print 'Fix so fail'

if __name__ == '__main__' :
	main()

