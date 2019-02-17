#!/usr/bin/python

"""

-- save as /opt/cni/bin/fran-cni

{
  "cniVersion": "0.3.1",
  "interfaces": [
      {
          "name": "eth0",
          "mac": "a2:a6:39:94:24:ef",
          "sandbox": "/proc/4941/ns/net"
      }
  ],
  "ips": [
      {
          "version": "4",
          "address": "10.244.1.2/24",
          "gateway": "10.244.1.1",
          "interface": 0
      }
  ]
}
"""
import sys
import os
import time
import subprocess
import random

with open('/var/log/fran.log', 'a') as the_file:
	the_file.write("FRAN called! \n  oper={}\n  CONT_ID={}\n  ".format( os.environ['CNI_COMMAND'], os.environ['CNI_CONTAINERID'] ))
	the_file.write("Netns={}\n  Ifname={}\n  Args={}\n  Path={} \n".format( os.environ['CNI_NETNS'], os.environ['CNI_IFNAME'], os.environ['CNI_ARGS'], os.environ['CNI_PATH']))

	for line in iter(sys.stdin.readline, ''):
    		the_file.write(' stdin={}\n'.format(line))

	the_file.write("\n")

	ret = """
{
  "cniVersion": "0.3.1",
  "interfaces": [
      {
          "name": "eth0",
          "mac": "%s",
          "sandbox": "%s"
      }
  ],
  "ips": [
      {
          "version": "4",
          "address": "%s/24",
          "gateway": "10.244.1.1",
          "interface": 0
      }
  ]
}
	"""
	
	if os.environ['CNI_COMMAND'] == 'ADD':
		os.system("mkdir -p /var/run/netns/")
		
		
		ifname = os.environ['CNI_IFNAME']
		containerid = os.environ['CNI_CONTAINERID']
		netns = os.environ['CNI_NETNS']
		host_if_name="veth{}".format(random.randint(100,10000))
		containerip = "10.244.1.{}".format(random.randint(2,254))
		gw_ip = "10.244.1.1"


		cmd = "ln -sfT %s /var/run/netns/%s"
		cmd = cmd % (netns, containerid)
		r = os.system(cmd)
		the_file.write(" Cmd={} ret={}\n".format(cmd, r))

		cmd = "ip link add %s type veth peer name %s"
		cmd = cmd % (ifname, host_if_name)
		r = os.system(cmd)
		the_file.write(" Cmd={} ret={}\n".format(cmd, r))

		cmd = "ip link set %s up"
		cmd = cmd % host_if_name
		r = os.system(cmd)
		the_file.write(" Cmd={} ret={}\n".format(cmd, r))

		cmd = "ip link set %s master cni0"
		cmd = cmd % host_if_name
		r = os.system(cmd)
		the_file.write(" Cmd={} ret={}\n".format(cmd, r))

		cmd = "ip link set %s netns %s"
		cmd = cmd % (ifname, containerid)
		r = os.system(cmd)
		the_file.write(" Cmd={} ret={}\n".format(cmd, r))

		cmd = "ip netns exec %s ip link set %s up"
		cmd = cmd % (containerid, ifname)
		r = os.system(cmd)
		the_file.write(" Cmd={} ret={}\n".format(cmd, r))

		cmd = "ip netns exec %s ip addr add %s/24 dev %s"
		cmd = cmd % (containerid, containerip, ifname)
		r = os.system(cmd)
		the_file.write(" Cmd={} ret={}\n".format(cmd, r))

		cmd = "ip netns exec %s ip route add default via %s dev %s"
		cmd = cmd % (containerid, gw_ip, ifname)
		r = os.system(cmd)
		the_file.write(" Cmd={} ret={}\n".format(cmd, r))
	
		cmd = "ip netns exec %s ip link show eth0 | awk '/ether/ {print $2}'"
		cmd = cmd % containerid
		mi_mac = subprocess.check_output(cmd, shell=True).rstrip()
		the_file.write(" Cmd={} ret={}\n".format(cmd, mi_mac))
	
		ret = ret % (mi_mac,netns, containerip)
		the_file.write(" mi_mac={} Out={}".format(mi_mac,ret))
		print(ret)

sys.exit(0)

