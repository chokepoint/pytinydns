#!/usr/bin/python
"""PyTinyDNS docstring.

This script acts as a light A record DNS resolver.
pyvpndns.conf should contain a list of domains and address resolutions

Example:
google.com.:127.0.0.1

The above would resolve any requests for google.com to 127.0.0.1
"""
import getopt
import socket
import sys

# DNSQuery class from http://code.activestate.com/recipes/491264-mini-fake-dns-server/
class DNSQuery:
	def __init__(self, data):
		self.data=data
		self.domain=''

		tipo = (ord(data[2]) >> 3) & 15   # Opcode bits
		if tipo == 0:                     # Standard query
			ini=12
			lon=ord(data[ini])
			while lon != 0:
				self.domain+=data[ini+1:ini+lon+1]+'.'
				ini+=lon+1
				lon=ord(data[ini])

	def build_reply(self, ip):
		packet=''
		if self.domain:
			packet+=self.data[:2] + "\x81\x80"
			packet+=self.data[4:6] + self.data[4:6] + '\x00\x00\x00\x00'   # Questions and Answers Counts
			packet+=self.data[12:]                                         # Original Domain Name Question
			packet+='\xc0\x0c'                                             # Pointer to domain name
			packet+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
			packet+=str.join('',map(lambda x: chr(int(x)), ip.split('.'))) # 4bytes of IP
		return packet

def print_help():
	print 'Usage: pytinydns.py [OPTION]...'
	print '\t-h, --help \t\tPrint this message'
	print '\t-c, --config=config\tSpecify config file to use'
	print '\t-d, --default=ip\tSpecify the default IP address to fall back on'

def read_config(config):
	cfile = open(config,"r")
	
	dns_dict = {}
	
	for line in cfile:
		sline = line.split(':')
		if len(sline) != 2 and line[0] != '#':
			print 'Invalid config format.'
			print 'google.com.:127.0.0.1'
			sys.exit(1)
	
		if line[0] != '#':
			dns_dict[sline[0]] = sline[1][0:-1] # trim \n off at the end of the line
	
	return dns_dict
	
def main():
	default_ip='127.0.0.1' # If the specified domain isn't in the config file, fall back to this
	no_config = True

	try:
		opts, args = getopt.getopt(sys.argv[1:], "hc:d:", ["help","config=","default="])
	except getopt.error, msg:
		print msg
		print_help()
		sys.exit(2)
	
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print_help()
			sys.exit(0)
		elif opt in ('-c', '--config'):
			config_file = arg
			no_config = False
		elif opt in ('-d', '--default'):
			default_ip = arg
	
	print '[-] PyTinyDNS'
	
	if (no_config == False):
		dns_dict = read_config(config_file)
  
	udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	udps.bind(('',53))
  
	try:
		while 1:
			data, addr = udps.recvfrom(1024)
			p=DNSQuery(data)
			if no_config == False and p.domain in dns_dict:
				udps.sendto(p.build_reply(dns_dict[p.domain]), addr)
				print '[+] Request from %s: %s -> %s' % (addr[0], p.domain, dns_dict[p.domain])
			else:
				udps.sendto(p.build_reply(default_ip), addr)
				print '[+] Request from %s: %s -> %s' % (addr[0], p.domain, default_ip)  
	except KeyboardInterrupt:
		print '[-] Ending'
		udps.close()

if __name__ == '__main__':
	main()
