#!/usr/bin/python
"""
redis_import.py

Import a host file into a redis database for live updating of PyTinyDNS

Host files have the following format host:ip

google.com.:192.168.1.1

resolves google.com to 192.168.1.1
"""
import redis
import sys

def import_config(config, redis_addr):
	print '[+] Opening File %s' % (config)
	
	try:
		cfile = open(config,"r")
	except:
		print '[-] File %s could not be found.' % (config)
		sys.exit(1)
	print "[+] Connecting to redis server %s" % (redis_addr)
	r_server = redis.Redis(redis_addr)
	
	for line in cfile:
		sline = line.split(':')
		if len(sline) != 2 and line[0] != '#':
			print 'Invalid config format.'
			print 'google.com.:127.0.0.1'
			sys.exit(1)
		else:
			if line[0] != '#':
				try:
					print '[+] Importing record: %s -> %s' % (sline[0],sline[1][0:-1])
					r_server.set(sline[0], sline[1][0:-1]) # trim \n off at the end of the line
				except:
					print '[-] Connection failed with server %s' % (redis_addr)
					sys.exit(1)
	print '[-] Import Complete'
def main():
	if len(sys.argv) == 1:
		print 'Usage: redis_import.py import_file'
		sys.exit(2)
		
	print '[-] PyTinyDNS Redis Import Tool'
		
	redis_addr = 'localhost'

	import_config(sys.argv[1], redis_addr)
	
	

if __name__ == '__main__':
	main()
