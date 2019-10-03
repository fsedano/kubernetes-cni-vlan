#!/usr/bin/python3

import unittest
from unittest import mock
import labmon_cni

MOCKED_K8S_PARAMS = {
    'CNI_COMMAND' : 'ADD',
    'CNI_CONTAINERID' : "xxxx",
    'CNI_NETNS' : "33efdij",
    'CNI_IFNAME' : 'net1',
    'CNI_ARGS' : 'ARG1=1;K8S_POD_NAME=MY_POD_NAME',
    'CNI_PATH' : '/bin'
}

MOCKED_INTERFACE_MAPS = [
    {"interface":"net1","vlan":519,"ip":"1.1.1.1","netmask":""},
    {"interface":"net2","vlan":520,"ip":"2.2.2.2","netmask":""}
]

class lmUnitTest(unittest.TestCase):
    @mock.patch('labmon_cni.K8s_Params.get_k8s_params')
    @mock.patch('labmon_cni.K8s_Params.get_interface_maps')
    @mock.patch('labmon_cni.OSexec.exec')
    def test_one(self,
        labmon_cni_OSexec_exec,
        labmon_cni_K8s_Params_get_interface_maps,
        labmon_cni_K8s_Params_get_k8s_params):
        labmon_cni_K8s_Params_get_k8s_params.return_value = MOCKED_K8S_PARAMS
        labmon_cni_K8s_Params_get_interface_maps.return_value = MOCKED_INTERFACE_MAPS
        labmon_cni_OSexec_exec.return_value = ""
        K8 = labmon_cni.K8s_CNI()
        K8.entrypoint()
        

unittest.main()