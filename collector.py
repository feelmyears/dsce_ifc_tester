from enum import Enum
import itertools
import random
import subprocess
from subprocess import call
from urllib.parse import urlparse
import os
import argparse
import configparser
from time import sleep
import csv

# class ProxyConfig(Enum):
# 	BYPASS_PROXY_HTTPS 	= 0		# Client 				->  (bypass)ProxyClient -> ***  HTTPS  ***  ->  (bypass)ProxyServer -> WebServer
# 	BYPASS_PROXY_QUIC 	= 1		# Client(QUIC Request) 	->  (bypass)ProxyClient -> ***  QUIC   ***  ->  (bypass)ProxyServer -> WebServer
# 	HTTP_PROXY_HTTPS 	= 2		# Client 				->          ProxyClient -> ***  HTTPS  ***  ->          ProxyServer -> WebServer
# 	QUIC_PROXY_QUIC 	= 3		# Client(QUIC Request) 	->  		ProxyClient -> ***  QUIC   ***  ->          ProxyServer -> WebServer
# 	HTTP_PROXY_QUIC 	= 4		# Client 				->          ProxyClient -> ***  QUIC   ***  ->          ProxyServer -> WebServer



class ProxyConfig(Enum):
	BYPASS_PROXY 		= 0		# Client 				->  (bypass)ProxyClient -> ***  QUIC  ***  ->  (bypass)ProxyServer -> WebServer
	QUIC_PROXY 	 		= 1 	# Client 				->          ProxyClient -> ***  QUIC  ***  ->          ProxyServer -> WebServer


class ServiceConfig(Enum):
	# NORMAL 	= 0		# No service degredation
	DA2GC 	= 1		# Direct Air to Ground Connection
	# MSS 	= 2		# Mobile Satellite Service

class TestConfig:
	# PROXY_PORTS = {
	# 	ProxyConfig.BYPASS_PROXY_HTTPS 	: 80,
	# 	ProxyConfig.BYPASS_PROXY_QUIC	: 443,
	# 	ProxyConfig.HTTP_PROXY_HTTPS 	: 18080,
	# 	ProxyConfig.QUIC_PROXY_QUIC 	: 18443,
	# 	ProxyConfig.HTTP_PROXY_QUIC 	: 18443,
	# }

	PROXY_PORTS = {
		ProxyConfig.BYPASS_PROXY 	    : 80,
		ProxyConfig.QUIC_PROXY			: 18443,
	}

	def __init__(self, proxy_config, service_config):
		self.proxy_config = proxy_config
		self.service_config = service_config

	def configure_router(self, router):
		# SSH into router
		# Reset service degradation  settings
		# Set service degration to desired settings
		# if self.service_config == ServiceConfig.NORMAL:
			# pass
		# elif self.service_config == ServiceConfig.DA2GC:
			# pass
		# elif self.service_config == ServiceConfig.MSS:
			# pass
		# else:
			# raise Exception('Unrecognized router configuration provided!')

		pass


	def configure_chrome(self, chrome_path, remote_debugging_port):

		cmd = f'{chrome_path} --user-data-dir=/tmp/chrome  --headless --remote-debugging-port=9222'
		proxy_port = self.PROXY_PORTS[self.proxy_config]

		if   self.proxy_config == ProxyConfig.BYPASS_PROXY:
			pass
		elif self.proxy_config == ProxyConfig.QUIC_PROXY:
			cmd += f' --proxy-server="localhost:18443"'
		
		print(cmd)
		p  = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
		return p

class Router:
	def __init__(self, address, user, password):
		self.address = address
		self.user = user
		self.password = password

class TestRunner:
	def __init__(self, websites, chrome_path, remote_debugging_port, output, repeat, timeout, max_attempts, router):
		"""
			websites 		list of websites to test
			chrome_path		path to installation of chrome
			debugging_port	remote debugging port for chrome
			output			path of output directory where results are saved
			repeat			number of times to repeat each test
			timeout			timeout for each test
			max_attempts	maximum number of times to try after a timeout
			router 			Router class for service emulation
		"""

		self.websites = websites
		self.chrome_path = chrome_path
		self.output = output
		self.repeat = repeat
		self.max_attempts = max(1, max_attempts)
		self.router = router
		self.remote_debugging_port = remote_debugging_port
		self.timeout = timeout
		self.failure_path = os.path.join(self.output, 'failures.csv')
		ensure_exists(self.failure_path)
		with open(os.path.join(self.failure_path), 'w') as f:
			writer = csv.writer(f)
			writer.writerow(['Website', 'Service Configuration', 'Proxy Configuration', 'Run Index', 'Total Attempts'])

	def run_tests(self):
		# Iterate all websites
		for i, website in enumerate(self.websites):
			for test_config in self.randomize_configs():
				for run_index in range(repeat):
					self.run(website, test_config, run_index)

	def run(self, site, test_config, run_index):
		hostname_parts = urlparse(site).hostname.split('.')
		hostname = None		
		if len(hostname_parts) > 2:
			hostname = hostname_parts[1]
		else:
			hostname = hostname_parts[0]


		service = test_config.service_config.name
		proxy = test_config.proxy_config.name
		output_path = self.get_run_output_path(hostname, service, proxy, run_index)

		for attempt in range(self.max_attempts):
			test_config.configure_router(self.router)
			chrome = test_config.configure_chrome(self.chrome_path, self.remote_debugging_port)
			sleep(3)

			har_capturer = self.capture_har(site, output_path)
			sleep(1)
			success = False
			try:
				har_capturer.wait(self.timeout)
				success = True
			except:
				print(f'Failed attempt #{attempt} for test <{service}, {proxy}, {run_index}>')


			har_capturer.kill()
			sleep(1)
			#chrome.kill()
			#os.system("killall -9 "Google Chrome")
			call(["killall", "-9", "Google Chrome"])
			sleep(1)
			if os.path.exists(output_path) and os.path.getsize(output_path) <= 275:
				success = False
				os.remove(output_path)
			
			if success is not True:
				continue
			else:
				return

		self.record_test_failure(site, test_config, run_index)

	def capture_har(self, site, output_path):
		cmd = f'node node_modules/chrome-har-capturer/bin/cli.js -o {output_path} {site}'
		p  = subprocess.Popen(cmd, shell=True)
		return p

	def get_run_output_path(self, hostname, service, proxy, run_index):
		ensure_exists(os.path.join(self.output, hostname) + '/')
		return os.path.join(self.output, hostname, f'{service}-{proxy}-{run_index}.har')

	def randomize_configs(self):
		configs = [TestConfig(pc, sc) for (pc, sc) in itertools.product(ProxyConfig, ServiceConfig)]
		random.shuffle(configs)
		return configs

	def record_test_failure(self, site, test_config, run_index):
		with open(os.path.join(self.failure_path), 'a') as f:
			writer = csv.writer(f)
			writer.writerow([site, test_config.service_config.name, test_config.proxy_config.name, run_index, self.max_attempts])

def ensure_exists(file_path):
	print('ensuring exists', file_path)
	directory = os.path.dirname(file_path)
	print(directory)
	if not os.path.exists(directory):
		print('directory dne')
		os.makedirs(directory)


def read_sites(path):
	with open(path, 'r') as f:
		return [url.strip() for url in f.readlines()]

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('--config', '-c', help="Configuration file", required=True)
	parser.add_argument('--mode', '-m', help="Configuration section in config file", default='DEFAULT')
	args = parser.parse_args()

	config = configparser.ConfigParser()
	config.read(args.config)

	default_config = config[args.mode]
	output_dir = default_config['sites'].split('.')[0]
	ensure_exists(output_dir  + '/.')

	router_addr = str(default_config['router_addr'])
	router_user = str(default_config['router_user'])
	router_password = str(default_config['router_password'])
	router = Router(router_addr, router_user, router_password)

	urls = read_sites(default_config['sites'])
	chrome = default_config['chrome']
	print(chrome)
	repeat = int(default_config['repeat'])
	max_attempts = int(default_config['max_attempts'])
	timeout = int(default_config['timeout'])

	remote_debugging_port = 9222
	tr = TestRunner(urls, chrome, remote_debugging_port, output_dir, repeat, timeout, max_attempts, router)
	tr.run_tests()
