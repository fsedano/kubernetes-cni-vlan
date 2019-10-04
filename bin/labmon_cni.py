#!/usr/bin/python3
import sys
import os
import time
import subprocess
import random
from kubernetes import client, config
import json
import ipaddress

MASTER_INTERFACE_NAME = "ens192"
class K8s_Params:
    def __init__(self):
        self.k8s_data = self.get_k8s_params()
        self.pod_data = self.get_pod_data()


    def get_pod_data(self):
        input_data = dict(s.split('=') for s in self.k8s_data['CNI_ARGS'].split(';'))
        print(f"Input data is {input_data}\n")
        data = {}
        data['K8S_POD_NAME'] = input_data['K8S_POD_NAME']
        data['K8S_POD_NAMESPACE'] = input_data['K8S_POD_NAMESPACE']
        return data

    def get_k8s_params(self):
        k8s_data =  {}
        k8s_data['CNI_COMMAND'] = os.environ['CNI_COMMAND']
        k8s_data['CNI_CONTAINERID'] = os.environ['CNI_CONTAINERID']
        k8s_data['CNI_NETNS'] = os.environ['CNI_NETNS']
        k8s_data['CNI_IFNAME'] = os.environ['CNI_IFNAME']
        k8s_data['CNI_ARGS'] = os.environ['CNI_ARGS']
        k8s_data['CNI_PATH'] = os.environ['CNI_PATH']
        return k8s_data

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
    
    def get_interface_maps(self, pod_name, netns):
        return {}

class OSexec:
    @classmethod
    def exec(self, cmd):
        print(f"EXEC: CALLING {cmd}\n")
        rc = subprocess.check_output(cmd, shell=True).decode()
        return rc

class CNIInterface:
    def __init__(self, interface_data):
        self.interface_data = interface_data

    def bringup(self):
        print(f"Interface data is {self.interface_data}\n")
        vlan = self.interface_data['vlan']
        br_name = f"phy_{vlan}"

        OSexec.exec(f"modprobe --first-time 8021q")
        OSexec.exec(f"ip link set {MASTER_INTERFACE_NAME} up")
        OSexec.exec(f"ip link add link {MASTER_INTERFACE_NAME} name {MASTER_INTERFACE_NAME}.{vlan} type vlan id {vlan}")
        OSexec.exec(f"ip link set {MASTER_INTERFACE_NAME}.{vlan} up")
        OSexec.exec(f"brctl addbr {br_name}")
        OSexec.exec(f"brctl addif {br_name} {MASTER_INTERFACE_NAME}.{vlan}")
        OSexec.exec(f"ip link set {br_name} up")
        OSexec.exec(f"iptables -A FORWARD -i {br_name}  -j ACCEPT")



class K8s_CNI:
    def __init__(self):
        self.k = K8s_Params()
        self.OS = OSexec()

    def oper_add(self):
        print("In oper add!")
        #rc = self.OS.exec("ls")
        #print(f"RC is {rc}")
        k = self.k
        #container_id = k.container_id()
        interface_data = k.get_interface_maps(k.pod_name(), k.netns())

        # Loop thru the interfaces
        for interface_data in k.get_interface_maps(k.pod_name(), k.netns()):
            print(f"Interface is {interface_data}")
            CNIInterface(interface_data).bringup()

    def oper_del(self):
        print("In oper DEL!")

    def entrypoint(self):
        if self.k.is_command_add():
            self.oper_add()
        if self.k.is_command_del():
            self.oper_del()