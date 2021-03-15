# -*- coding:utf-8 -*-

def get_byte(str):
	return ord(str)


def get_word(str):
	return ord(str[0]) | (ord(str[1]) << 8)


def get_dword(str):
	return ord(str[0]) | (ord(str[1]) << 8) | (ord(str[2]) << 16) | (ord(str[3]) << 24)


def set_dword(data, off, dword):
	pass


def fix_program_table_element(data, offset):
	newdata = ''
	p_offset_off = offset + 4
	p_vaddr_off = offset + 8
	p_paddr_off = offset + 12
	p_offset = get_dword(data[p_offset_off:p_offset_off + 4])
	p_vaddr = get_dword(data[p_vaddr_off:p_vaddr_off + 4])
	p_paddr = get_dword(data[p_paddr_off:p_paddr_off + 4])
	if p_vaddr != p_paddr:
		return 'Error Found'
	elif p_offset != p_vaddr:
		newdata = data[0:p_offset_off] + chr(p_vaddr & 0xff) + chr((p_vaddr >> 8) & 0xff) + chr(
			(p_vaddr >> 16) & 0xff) + chr((p_vaddr >> 24) & 0xff) + data[p_offset_off + 4:]
	# newdata[p_offset_off] = chr(p_vaddr & 0xff)
	# newdata[p_offset_off + 1] = chr((p_vaddr >> 8) & 0xff)
	# newdata[p_offset_off + 2] = chr((p_vaddr >> 16) & 0xff)
	# newdata[p_offset_off + 3] = chr((p_vaddr >> 24) & 0xff)
	else:
		newdata = data
	return newdata


def fix_program_table_element7_data(data, base_addr):
	i = 0
	newdata = data
	while i < len(data):
		num_org = get_dword(data[i:i + 4])
		if (num_org > base_addr) and (num_org & 0x7fffff00 != 0x7fffff00):
			num_new = num_org - base_addr
			newdata = newdata[:i] + chr(num_new & 0xff) + chr((num_new >> 8) & 0xff) + chr(
				(num_new >> 16) & 0xff) + chr((num_new >> 24) & 0xff) + newdata[i + 4:]
		i = i + 4
	return newdata


def fix_sofile(str_file_input, str_file_output, base_addr):
	try:
		file_input = open(str_file_input, 'rb')
		data_org = file_input.read()
		file_input.close()
	except IOError, e:
		print e
		return 1

	e_phoff = get_dword(data_org[0x1c:0x1c + 4])
	e_ehsize = get_byte(data_org[0x28])
	e_phentsize = get_word(data_org[0x2a:0x2a + 2])
	e_phnum = get_word(data_org[0x2c:0x2c + 2])

	for phnum in range(0, e_phnum):
		phoff = e_phoff + phnum * e_phentsize
		data_org = fix_program_table_element(data_org, phoff)

	p_offset = get_dword(data_org[phoff + 4:phoff + 8])
	p_filesz = get_dword(data_org[phoff + 16:phoff + 20])
	# 根据基数修复函数列表
	data_fixed = fix_program_table_element7_data(data_org[p_offset:p_offset + p_filesz], base_addr)
	data_org = data_org[:p_offset] + data_fixed + data_org[p_offset + p_filesz:]

	try:
		file_out = open(str_file_output, 'wb')
		file_out.write(data_org)
		file_out.close()
	except IOError, e:
		print e
		return 1

	return 0


if __name__ == '__main__':
	result = fix_sofile('d:\\dump.so', 'd:\\fix_dump.so', 0x79efa000)
	if 0 == result:
		raw_input('Program Finish')
	else:
		raw_input('enterkey to exit')