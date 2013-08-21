#!/usr/bin/python
"""PyTinyDNS docstring.

This script acts as a light A record DNS resolver.
Use redis_import.py to import a host file into a live DB.
You can also use pydns.conf as a flat file config with no DB.

Example:
# Comment
google.com.:127.0.0.1

The above would resolve any requests for google.com to 127.0.0.1
"""
import getopt
import redis
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
	print '\t-d, --default=ip\tSpecify the default IP address to fall back on'
	print '\t-l, --list=host_file\tSpecify host file to use instead of redis'
	print '\t-n, --noredis\t\tSpecify not to use redis db. Default IP will be used'

def read_config(config):
	cfile = open(config,"r")

	dns_dict = {}

	for line in cfile:
		sline = line.split(':')
		if len(sline) != 2 and line[0] != '#':
			print 'Invalid config format.'
			print 'google.com.:127.0.0.1'
			sys.exit(1)
		else:
			if line[0] != '#':
				dns_dict[sline[0]] = sline[1][0:-1] # trim \n off at the end of the line
	
	return dns_dict
	
def main():
	default_ip='127.0.0.1' # If the specified domain isn't in the config file, fall back to this
	redis_addr='localhost' # redis server to connect to
	no_redis = False
	dns_dict = {}
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hnd:l:", ["list=", "noredis", "help", "default="])
	except getopt.error, msg:
		print msg
		print_help()
		sys.exit(2)
	
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print_help()
			sys.exit(0)
		elif opt in ('-n', '--noredis'):
			no_redis = True
		elif opt in ('-d', '--default'):
			default_ip = arg
		elif opt in ('-l', '--list'):
			no_redis = True
			dns_dict = read_config(arg)
	
	print '[-] PyTinyDNS'
	
	if no_redis == False:
			r_server = redis.Redis(redis_addr)
  
	udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	udps.bind(('',53))
  
	try:
		while 1:
			data, addr = udps.recvfrom(1024)
			p=DNSQuery(data)
			if no_redis == False: # We're using redis. Check if the key exists.
				try:
					a_record = r_server.get(p.domain)
				except:
					print 'No redis server connection with %s.' % (redis_addr) # No connection with redis: fall back to default
					a_record = default_ip
				if a_record:      # A record returned from redis DB
					ip = a_record
				else:             # No record returned: fall back to default.
					ip = default_ip
			else:				  # Not using redis: fall back to default.
				if p.domain in dns_dict:
					ip = dns_dict[p.domain]
				else:
					ip = default_ip
			
			udps.sendto(p.build_reply(ip), addr)
			print '[+] Request from %s: %s -> %s' % (addr[0], p.domain, ip) 
	except KeyboardInterrupt:
		print '[-] Ending'
		udps.close()

if __name__ == '__main__':
	main()
