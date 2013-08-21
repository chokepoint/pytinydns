#!/usr/bin/python
"""
redis_import.py

Import a host file into a redis database for live updating of PyTinyDNS

Host files have the following format host:ip

google.com.:192.168.1.1

resolves google.com to 192.168.1.1
"""
import getopt
import redis
import sys

def import_config(config, redis_addr):
	print '[+] Opening File %s' % (config)
	
	try:
		cfile = open(config,"r")
	except:
		print '[-] File %s could not be found.' % (config)
		sys.exit(1)
	
	for line in cfile:
		sline = line.split(':')
		if len(sline) != 2 and line[0] != '#':
			print 'Invalid config format.'
			print 'google.com.:127.0.0.1'
			sys.exit(1)
		else:
			if line[0] != '#':
				domain = sline[0]
				ip = sline[1][0:-1]
				insert_record(domain,ip,redis_addr)
	
def insert_record(domain,ip,redis_addr):
	r_server = redis.Redis(redis_addr)

	try:
		print '[+] Importing record: %s -> %s' % (domain,ip)
		r_server.set(domain, ip) 
	except:
		print '[-] Connection failed with server %s' % (redis_addr)
		sys.exit(1)

def print_help():
	print 'Usage: redis_import.py OPTIONS'
	print '\t-h, --help\t\tPrint this message'
	print '\t-l, --list=host_file\tImport host file'
	print '\t-u, --update=host:ip\tUpdate one record'

def main():
	redis_addr = 'localhost'
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hu:l:", ["update=","list=", "help"])
	except getopt.error, msg:
		print msg
		print_help()
		sys.exit(2)
	
	print '[-] PyTinyDNS Redis Import Tool'	
	
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print_help()
			sys.exit(0)
		elif opt in ('-u', '--update'):
			sarg = arg.split(':')
			insert_record(sarg[0],sarg[1],redis_addr)
		elif opt in ('-l', '--list'):
			print arg
			import_config(arg,redis_addr)

	print '[-] Import Complete'
	

if __name__ == '__main__':
	main()
