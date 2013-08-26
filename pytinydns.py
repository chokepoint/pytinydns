#!/usr/bin/env python
"""PyTinyDNS docstring.

This script acts as a light A record DNS resolver.
Use redis_import.py to import a host file into a live DB.
You can also use pydns.conf as a flat file config with no DB.

Example:
# Comment
google.com.:127.0.0.1

The above would resolve any requests for google.com to 127.0.0.1
"""
import ConfigParser
import getopt
import redis
import socket
import sys

try:
	socket.SO_REUSEPORT
except AttributeError:
	socket.SO_REUSEPORT = 15

#Global variables
default_ip = '127.0.0.1'
redis_server = 'localhost'
use_redis = True
resolve_nonmatch = False
dns_dict = {}

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
		if ip == '': # Taken from crypt0s (https://github.com/Crypt0s/FakeDns/blob/master/fakedns.py)
			# Build the response packet         
			packet+=self.data[:2] + "\x81\x83"                         # Reply Code: No Such Name
																	   #0 answer rrs   0 additional, 0 auth
			packet+=self.data[4:6] + '\x00\x00' + '\x00\x00\x00\x00'   # Questions and Answers Counts
			packet+=self.data[12:]                                     # Original Domain Name Question
		
		if self.domain and packet == '':
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
	print '\t-c, --config=file\tSpecify the config file to use'
	print '\t-d, --default=ip\tSpecify the default IP address to fall back on'
	print '\t-l, --list=host_file\tSpecify host file to use instead of redis'
	print '\t-n, --noredis\t\tSpecify not to use redis db. Default IP will be used'
	print '\t-r, --resolve\t\tSpecify to resolve non matches to actual IP'

def read_hosts(config):
	# Use global dns dictionary
	global dns_dict
	
	try:
		c_file = open(config,"r")
	except:
		print '[-] Host file %s not found.' % (config)
		sys.exit(1)

	for line in c_file:
		sline = line.split(':')
		if len(sline) != 2 and line[0] != '#':
			print 'Invalid config format.'
			print 'google.com.:127.0.0.1'
			sys.exit(1)
		else:
			if line[0] != '#': 						 # Make sure the line is not a comment
				dns_dict[sline[0]] = sline[1][0:-1]  # trim \n off at the end of the line
	
def read_config(config):
	# Use global config variables
	global default_ip
	global redis_server
	global use_redis
	global resolve_nonmatch
	
	c_parse = ConfigParser.ConfigParser()
	
	try:
		c_parse.read(config)
	except:
		print '[-] Config file %s not found.' % (config)
		sys.exit(1)
	
	for item in c_parse.items('PyTinyDNS'):
		arg = item[1]
		opt = item[0]
		
		if opt == 'defaultip':
			default_ip = arg
		elif opt == 'use_redis':
			if arg == 'yes':
				use_redis = True
			elif arg == 'no':
				use_redis = False
		elif opt == 'redis_server':
			redis_server = arg
		elif opt == 'host_file':
			read_hosts(arg)
		elif opt == 'resolve_nonmatch':
			if arg == 'yes':
				resolve_nonmatch = True
			elif arg == 'no':
				resolve_nonmatch = False

# Make request to external DNS (used when resolve_nonmatch = True)
def ext_request(domain):
	try:
		return socket.gethostbyname(domain)
	except: # Domain doesn't exist
		print '[-] Unable to parse request'
		return ''
	
def main():
	# Use global config variables
	global default_ip
	global redis_server
	global use_redis
	global resolve_nonmatch
	global dns_dict
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hrnc:d:l:", ["resolve", "config=", "list=", "noredis", "help", "default="])
	except getopt.error, msg:
		print msg
		print_help()
		sys.exit(2)
	
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print_help()
			sys.exit(0)
		elif opt in ('-n', '--noredis'):
			use_redis = False
		elif opt in ('-d', '--default'):
			default_ip = arg
		elif opt in ('-l', '--list'):
			use_redis = False
			dns_dict = read_hosts(arg)
		elif opt in ('-c', '--config'):
			read_config(arg)
		elif opt in ('-r', 'resolve'):
			resolve_nonmatch = True
	
	print '[-] PyTinyDNS'
	
	if use_redis == True:
			r_server = redis.Redis(redis_server)
  
	udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	#SO_REUSEPORT option allows multiple threads to bind to one port.
	# kernel >= 3.9 https://lwn.net/Articles/542629/
	try: 
		udps.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
	except socket.error:
		print '[-] SO_REUSEPORT not supported by your system.'
	
	udps.bind(('',53))
  
	try:
		while 1:
			ip = ''
			data, src_addr = udps.recvfrom(1024)
			p=DNSQuery(data)
			if use_redis == True: # We're using redis. Check if the key exists.
			
				try: # Try to find domain using redis
					a_record = r_server.hget('pytinydns.domains', p.domain)
				except:
					print 'No redis server connection with %s.' % (redis_server) # No connection with redis: fall back to default
					a_record = default_ip
					
				if a_record is not None: # A record returned from redis DB
					ip = a_record
				else:  # No record returned
					if resolve_nonmatch == True:
						ip = ext_request(p.domain)
					else:
						ip = default_ip
						
			else:  # Not using redis: fall back to file or default.
				if p.domain in dns_dict:
					ip = dns_dict[p.domain]
				else:
					if resolve_nonmatch == True:
						ip = ext_request(p.domain)
					else:
						ip = default_ip
			
			udps.sendto(p.build_reply(ip), src_addr)
			print '[+] Request from %s: %s -> %s' % (src_addr[0], p.domain, ip) 
	except KeyboardInterrupt:
		print '[-] Ending'
		udps.close()

if __name__ == '__main__':
	main()
