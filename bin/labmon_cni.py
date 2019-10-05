#!/usr/bin/python3
import sys
import os
import time
import subprocess
import random
from kubernetes import client, config
import json
import ipaddress
import logging

MASTER_INTERFACE_NAME = "ens192"
class K8s_Params:
    def __init__(self):
        self.k8s_data = self.get_k8s_params()
        self.pod_data = self.get_pod_data()
        self.k8s_annotations = self.get_annotations(self.pod_name(),self.pod_namespace())


    def get_pod_data(self):
        input_data = dict(s.split('=') for s in self.k8s_data['CNI_ARGS'].split(';'))
        data = {}
        data['K8S_POD_NAME'] = input_data['K8S_POD_NAME']
        data['K8S_POD_NAMESPACE'] = input_data['K8S_POD_NAMESPACE']
        return data

    def get_k8s_params(self):
        k8s_data =  {}
        logging.info(f"Reading CNI info from environment {os.environ}")
        k8s_data['CNI_COMMAND'] = os.environ['CNI_COMMAND']
        k8s_data['CNI_CONTAINERID'] = os.environ['CNI_CONTAINERID']
        k8s_data['CNI_NETNS'] = os.environ['CNI_NETNS']
        k8s_data['CNI_IFNAME'] = os.environ['CNI_IFNAME']
        k8s_data['CNI_ARGS'] = os.environ['CNI_ARGS']
        k8s_data['CNI_PATH'] = os.environ['CNI_PATH']
        logging.info(f"Retrieved k8s params: {k8s_data}")
        return k8s_data

    def get_annotations(self, pod_name, pod_namespace):
        logging.info(f"Getting annotations for pod_name {pod_name} ns {pod_namespace}")
        config.load_kube_config()
        v1=client.CoreV1Api()
        annotations = {}
        try:
            data = v1.read_namespaced_pod(pod_name, pod_namespace)
            annotations = data.metadata.annotations
            logging.info(f"Annotations is {annotations}")
        except:
            logging.info("No interface data found")

        return annotations

    def get_interface_maps(self, annotations):
        try:
            return json.loads(annotations['cisco.epfl/interface_maps'])
        except:
            return []

    def add_old_style_interface_maps(self, interface_maps, annotations):
        logging.info(f"Adding old style annotations={annotations}")
        try:
            ip_address = annotations['cisco.epfl/ip_address']
            prefix_length = annotations['cisco.epfl/ip_prefix_length']
            vlan = annotations['cisco.epfl/vlan_id']
            IP = ipaddress.ip_interface(f"{ip_address}/{prefix_length}")

            map = {
                "interface" : "net1",
                "vlan" : vlan,
                "netmask" : str(IP.netmask),
                "ip" : ip_address
            }
            interface_maps.append(map)
        except:
            logging.exception("Data not found")
            pass
        return interface_maps
    #fixme getters
    def command(self):
        return self.k8s_data['CNI_COMMAND']

    def is_command_add(self):
        return self.command() == "ADD"

    def is_command_del(self):
        return self.command() == "DEL"

    def container_id(self):
        return self.k8s_data['CNI_CONTAINERID']

    def netns(self):
        return self.k8s_data['CNI_NETNS']

    def pod_name(self):
        return self.pod_data['K8S_POD_NAME']

    def pod_namespace(self):
        return self.pod_data['K8S_POD_NAMESPACE']

    def sanitize_interface_data(self,interface_maps):
        logging.info(f"List of interface maps to sanitize={interface_maps}")
        for map in interface_maps:
            logging.info(f"Processing IF_MAP to sanizite={map}")
            if map['netmask'] == "":
                map['netmask'] = "255.255.255.0"
        return interface_maps

class OSexec:
    @classmethod
    def exec(self, cmd):
        try:
            subprocess.check_output(cmd, shell=True).decode()
            logging.info(f" SUCCESS -> {cmd}")
        except:
            logging.info(f" FAILURE -> {cmd}")
            pass
    @classmethod
    def exec_get_output(self, cmd):
        rc = ""
        try:
            rc = subprocess.check_output(cmd, shell=True).decode()
            logging.info(f" SUCCESS -> {cmd}")
        except:
            logging.info(f" FAILURE -> {cmd}")
            pass
        return rc.rstrip()

class CNIInterface:
    def __init__(self, interface_data, k8s_params, index):
        self.interface_data = interface_data
        self.k8s_data = k8s_params
        self.output_interface_data = {}
        self.output_ip_data = {}
        self.index = index

    def bringup(self):
        logging.info("On interface bringup")
        vlan = self.interface_data['vlan']
        phy_name = f"phy_{vlan}"
        netns = self.k8s_data.netns()
        containerid = self.k8s_data.container_id()
        ifname = self.interface_data['interface']
        host_if_name = f"veth{vlan}"

        OSexec.exec(f"modprobe --first-time 8021q")
        OSexec.exec(f"ip link set {MASTER_INTERFACE_NAME} up")
        OSexec.exec(f"ip link add link {MASTER_INTERFACE_NAME} name {MASTER_INTERFACE_NAME}.{vlan} type vlan id {vlan}")
        OSexec.exec(f"ip link set {MASTER_INTERFACE_NAME}.{vlan} up")
        OSexec.exec(f"brctl addbr {phy_name}")
        OSexec.exec(f"brctl addif {phy_name} {MASTER_INTERFACE_NAME}.{vlan}")
        OSexec.exec(f"ip link set {phy_name} up")
        OSexec.exec(f"iptables -A FORWARD -i {phy_name}  -j ACCEPT")
        OSexec.exec(f"ln -sfT {netns} /var/run/netns/{containerid}")
        OSexec.exec(f"ip link add {ifname} type veth peer name {host_if_name}")
        OSexec.exec(f"ip link set {host_if_name} up")
        OSexec.exec(f"ip link set {host_if_name} master {phy_name}")
        OSexec.exec(f"ip link set {ifname} netns {containerid}")
        OSexec.exec(f"ip netns exec {containerid} ip link set {ifname} up")
        if self.interface_data['ip'] != "":
            IP = ipaddress.ip_interface(f"{self.interface_data['ip']}/{self.interface_data['netmask']}")
            OSexec.exec(f"ip netns exec {containerid} ip addr add {IP.with_prefixlen} dev {ifname}")
        cmd = "ip netns exec %s ip link show %s | awk '/ether/ {print $2}'"
        cmd = cmd % (containerid, ifname)
        if_mac = OSexec.exec_get_output(cmd)
        self.output_interface_data['mac'] = if_mac
        self.output_interface_data['name'] = ifname
        self.output_interface_data['sandbox'] = netns

        self.output_ip_data['version'] = "4"
        self.output_ip_data['address'] = IP.with_prefixlen
        self.output_ip_data['interface'] = self.index

    def teardown(self):
        logging.info("On interface teardown")
        vlan = self.interface_data['vlan']
        phy_name = f"phy_{vlan}"
        netns = self.k8s_data.netns()
        ifname = self.interface_data['interface']
        host_if_name = f"veth{vlan}"
        if self.interface_data['ip'] != "":
            IP = ipaddress.ip_interface(f"{self.interface_data['ip']}/{self.interface_data['netmask']}")

        OSexec.exec(f"ip link delete {MASTER_INTERFACE_NAME}.{vlan}")
        OSexec.exec(f"ip link delete {phy_name}")
        OSexec.exec(f"ip link delete {host_if_name}")
        OSexec.exec(f"iptables -D FORWARD -i {phy_name}  -j ACCEPT")
        self.output_interface_data['name'] = ifname
        self.output_interface_data['sandbox'] = netns

        self.output_ip_data['version'] = "4"
        self.output_ip_data['address'] = IP.with_prefixlen
        self.output_ip_data['interface'] = self.index



class K8s_CNI:
    def __init__(self):
        self.k = K8s_Params()
        self.OS = OSexec()

    def oper_add(self):
        logging.info("In oper add")
        interface_maps = self.prepare_interface_maps()
        # Loop thru the interfaces
        index = 0
        cni_result = {'cniVersion' : '0.3.1'}
        cni_interfaces = []
        cni_ips = []
        for interface_data in interface_maps:
            Interface = CNIInterface(interface_data, self.k, index)
            Interface.bringup()
            cni_interfaces.append(Interface.output_interface_data)
            cni_ips.append(Interface.output_ip_data)
            index = index + 1

        cni_result['interfaces'] = cni_interfaces
        cni_result['ips'] = cni_ips
        rc = json.dumps(cni_result, sort_keys=True, indent=4)
        logging.info(f"Processing done, retunring={rc}")
        print(rc)

    def prepare_interface_maps(self):
        k = self.k
        interface_maps = k.get_interface_maps(k.k8s_annotations)
        logging.info(f"STEP1: interface_maps is {interface_maps}")
        # Add old-style interface maps
        interface_maps = k.add_old_style_interface_maps(interface_maps, k.k8s_annotations)
        logging.info(f"STEP2: interface_maps is {interface_maps}")
        interface_maps = k.sanitize_interface_data(interface_maps)
        logging.info(f"STEP3: interface_maps is {interface_maps}")
        logging.info(f"INTERFACES DATA={interface_maps}")
        return interface_maps

    def oper_del(self):
        logging.info("In oper DEL")
        interface_maps = self.prepare_interface_maps()


        # Loop thru the interfaces
        index = 0
        cni_result = {'cniVersion' : '0.3.1'}
        cni_interfaces = []
        cni_ips = []
        logging.info(f"Interface data: {interface_maps}")
        for interface_data in interface_maps:
            Interface = CNIInterface(interface_data, self.k, index)
            Interface.teardown()
            cni_interfaces.append(Interface.output_interface_data)
            cni_ips.append(Interface.output_ip_data)
            index = index + 1

        cni_result['interfaces'] = cni_interfaces
        cni_result['ips'] = cni_ips
        rc = json.dumps(cni_result, sort_keys=True, indent=4)
        logging.info(f"Processing done, retunring={rc}")
        print(rc)


    def entrypoint(self):
        if self.k.is_command_add():
            self.oper_add()
        if self.k.is_command_del():
            self.oper_del()

### Entrypoint ###
if __name__ == "__main__":
    logging.basicConfig(filename='/tmp/app.log', filemode='a', format='%(asctime)s [%(process)d] - %(levelname)s - %(message)s', level=logging.DEBUG)
    try:
        K8s_CNI().entrypoint()
    except Exception as e:
        logging.exception(f"Exception on main")

    sys.exit(0)
