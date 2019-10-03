#!/usr/bin/python3

import unittest
from unittest import mock
#from code1 import c1
import code1
#from unittest.mock import Mock

class lmUnitTest(unittest.TestCase):
    #def setUp(self):
        #print("\nSetting up..\n")
        #self.directory = "direc.."
    #def test_two(self):
    #    x = code1.c1()
    #    x.m1()
    #    self.assertTrue(True)
    @mock.patch('code1.c2.m2')
    def test_three(self, mock_c2_m2): 
        print("+++ start test mocked ++++")
        mock_c2_m2.return_value = 99
        x = code1.c1()
        x.m1()

    def test_four(self):
        print("+++ start test NO MOCK ++++")
        x = code1.c1()
        x.m1()

unittest.main()