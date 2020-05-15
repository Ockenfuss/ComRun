import ComRun.UvspecExtractors as uvex
import numpy.testing as npt
import numpy as np
import unittest as ut

class UvexTest(ut.TestCase):
    def test_wctau_dis(self):
        with open('test/integration/fixtures/Wctau/wctau_dis.dat') as f:
            result=uvex.get_wctau_dis_fromstream(f)
        checkresult=np.array([[599.831543, 77.240723, 0.0], [600.453247, 77.242174, 1.4e-05], [600.80188, 77.24301, 3.2e-05], [601.435242, 77.244528, 5.5e-05], [602.335449, 77.246685, 8.7e-05], [602.585754, 77.247283, 9.2e-05], [603.195312, 77.248744, 0.00012], [603.859863, 77.250338, 0.000143], [604.22345, 77.251209, 0.000157], [604.929993, 77.252903, 0.00018], [605.525879, 77.254329, 0.000203], [606.12915, 77.255774, 0.00023], [606.623413, 77.256958, 0.000244], [607.052368, 77.257989, 0.000258], [607.692566, 77.259523, 0.000281], [608.317993, 77.261021, 0.000309], [608.830994, 77.262251, 0.000322], [609.294067, 77.263362, 0.000341], [609.871948, 77.264747, 0.000359]])
        npt.assert_almost_equal(checkresult, result)