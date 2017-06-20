import csv
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException,NetMikoAuthenticationException
from paramiko.ssh_exception import SSHException

# these are just simple python formatted files with variables in them
# the WLC IP and credentials are in here
from credentials import *

# first we want to grab all the APs that the WLC knows about

wlc = {
		'device_type': 'cisco_wlc',
		'ip': controller,
		'username': controller_u,
		'password': controller_p,
		'port' : 22,          # optional, defaults to 22
		'secret': secret,     # optional, defaults to ''
		'verbose': False,       # optional, defaults to False
	}

net_connect = ConnectHandler(**wlc)
ap_summary = net_connect.send_command('show ap summary').split("\n")

summary_start = 0
ap_on_wlc = []

# we put the APs into a list of dictionaries for easy reference later
for ap_summary_output in ap_summary:
	if "-" in ap_summary_output:
		summary_start = 1
	elif summary_start == 0:
		continue
	if len(ap_summary_output.split()) <= 0:
		continue
	ap_on_wlc.append({'MAC':ap_summary_output.split()[3],'IP':ap_summary_output.split()[7],'NAME':ap_summary_output.split()[0]})

# and close our SSH session
net_connect.disconnect()

# this loads the devices we're working with from a simple CSV file
# I often alter this file depending on what I'm working on
switches = csv.DictReader(open("switches.csv"))

for row in switches:	
	# this initializes the device object
	# it pulls the username/password/secret variables from a local file called 'credentials.py'
	# the IP is pulled from the 'switches.csv' file
	cisco_switch = {
		    'device_type': 'cisco_ios',
		    'ip': row['IP'],
		    'username': username,
		    'password': password,
		    'port' : 22,          # optional, defaults to 22
		    'secret': secret,     # optional, defaults to ''
		    'verbose': False,       # optional, defaults to False
		}
		
	try: # if the switch is reponsive we do our thing, otherwise we hit the exeption below
		# this actually logs into the device
		net_connect = ConnectHandler(**cisco_switch)
		# we gather a list of APs learned via CDP
		ap_cdp_neighbor = net_connect.send_command('sh cdp neigh | i AIR-AP380').split("\n")
		
		if len(ap_cdp_neighbor) > 1: # if there's nothing in CDP we skip it
			# and then we roll through the list one by one
			for ap_cdp_interface in ap_cdp_neighbor:
				ap_cdp_name = ap_cdp_interface.split()[0] if len(ap_cdp_interface.split()) >= 1 else 'null'
				# if the AP name is really long it gets stuck on another line
				# so we have to go deeper to fix it
				if "Gig" in ap_cdp_name:
					precise_name = 'sh cdp neigh gi ' + ap_cdp_interface.split()[1] + ' detail'
					ap_cdp_name = net_connect.send_command(precise_name).split()[3]
				# sometimes in CDP an AP is named AAPnnnn.nnnn.nnnn
				# and it is APnnnn.nnnn.nnnn on the WLC so we fix this
				if "AAP" in ap_cdp_name:
					ap_cdp_name = ap_cdp_name[1:]

				found = 0 # this tracks if we've got a match between the WLC and the switch CDP neighbors
				for ap in ap_on_wlc:
					if ap['NAME'] == ap_cdp_name:
						found = 1
				if not found:
					print row['Switch'] + "," + row['IP'] + "," + ap_cdp_name + "," + "Gi" + ap_cdp_interface.split()[2]
#				else:
#					print row['Switch'] + "," + row['IP']
			net_connect.disconnect()
#		else:
#			print row['Switch'] + "," + row['IP']
	except (NetMikoTimeoutException, NetMikoAuthenticationException):
		print row['Switch'] + "," + row['IP'] + ',no_response'
		

