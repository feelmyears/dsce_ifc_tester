#!/usr/bin/python

import os
import argparse
import subprocess
from time import sleep
from urllib.parse import urlparse

def read_sites(path):
	with open(path, 'r') as f:
		return [url.strip() for url in f.readlines()]

def start_chrome(chrome_path, remote_debugging_port):
#	cmd = f'/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --user-data-dir=/tmp/chrome  --proxy-server="localhost:8080"  --enable-quic --remote-debugging-port={remote_debugging_port} --headless  --proxy-server="quic://rodrigo918.hopto.org:443"'
	cmd = f'{chrome_path} --enable-quic --headless --remote-debugging-port={remote_debugging_port} --proxy-server="localhost:8080"'

	p  = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
#	p.communicate()
	return p

def capture_har(har_path, site):
	cmd = f'node node_modules/chrome-har-capturer/bin/cli.js -o {har_path} {site}'
	p  = subprocess.Popen(cmd, shell=True)
	return p

def ensure_dir(file_path):
	directory = os.path.dirname(file_path)
	if not os.path.exists(directory):
		os.makedirs(directory)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('--sites', '-s', help="Path to txt file of sites", type=str)
	parser.add_argument('--chrome', '-c', help="Path to Chrome installation", type=str)
	parser.add_argument('--output', '-o', help="Dir to save har files", type=str)
	args = parser.parse_args()

	output_dir = args.output
	ensure_dir(output_dir)

	test_urls = read_sites(args.sites)
	for i, url in enumerate(test_urls):
		hostname = urlparse(url).hostname.split('.')[1]

		p_browser = start_chrome(args.chrome, 9222)
		sleep(3)
		p_har = capture_har(os.path.join(output_dir, f'{i}_{hostname}.har'), url)
		sleep(10)

		p_har.kill()
		p_browser.kill()
