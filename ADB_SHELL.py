# -*- coding:utf-8 -*-

import os
import socket


class adbShell():
	"""adb shell的类"""

	def __init__(self):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.settimeout(10)

	def adb_send_command(self, command):
		"""adb发送指令"""
		self.socket.sendall('%04x' % (len(command)))
		self.socket.sendall(command)

	def adbshell_send_command(self, command):
		"""adb shell 发送指令"""
		req_msg = 'shell:%s' % (command)
		self.adb_send_command(req_msg)

	def adb_recvice(self, count):
		"""adb接收count个数据"""
		return self.socket.recv(count)

	def adb_recvice_data(self):
		"""adb接收完整的数据"""
		resp = self.adb_recvice(4)
		if 'OKAY' != resp:
			return [1, resp]
		rbuf = ''  # 以字符串的形式呈现
		while True:
			try:
				resp = self.adb_recvice(4096)
			except socket.error, e:
				break
			else:
				if 0 == len(resp):  # recv函数返回值为字符串,只能通过判断字符串长度来确定是否有数据接收
					break
				else:
					rbuf += resp
		return rbuf

	def adb_connect(self):
		"""创建链接"""
		while True:
			try:
				self.socket.connect(('127.0.0.1', 5037))
			except:
				os.system('adb start-server')
				continue
			else:
				break
		req_msg = 'host:transport-any'
		self.adb_send_command(req_msg)
		resp = self.adb_recvice(4)
		return resp  # 只返回结果,不进行判断

	def adb_server(self, command):
		"""adb服务"""
		conn_statue = self.adb_connect()
		if conn_statue != 'OKAY':
			return [1, 'unable to connect any devices']
		self.adbshell_send_command(command)
		recv_data = self.adb_recvice_data()
		return [0, recv_data]


if __name__ == '__main__':
	"""测试用"""
	test = adbShell()
	result = test.adb_server('ps')
	print result[1]
