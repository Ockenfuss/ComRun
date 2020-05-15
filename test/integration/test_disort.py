import unittest as ut
import numpy as np
import xarray as xr
import subprocess as sub
import numpy.testing as npt


def run(inifile):
    process=sub.Popen(f'python3 ComRun/Main.py {inifile}', shell=True)
    process.wait()


class DisortTests(ut.TestCase):
    def test_disort_radiance(self):
        inifile='test/integration/fixtures/test_disort_radiance.ini'
        outfile='test/integration/temp/test_disort_radiance.nc'
        run(inifile)
        data=xr.open_dataset(outfile)
        self.assertCountEqual(data.data_vars, ['time_all', 'radiance_dis'])
        self.assertCountEqual(data['time_all'].coords.keys(), ['wvl', 'umu', 'rt_type'])
        self.assertCountEqual(data['radiance_dis'].coords.keys(), ['wvl', 'umu', 'rad_umu', 'rad_wvl', 'rad_phi'])
        self.assertAlmostEqual(1.356163502e+01, data['radiance_dis'].sel(umu='-1.0', wvl='600', rad_wvl=599.970, rad_umu=-1).values[0])
        self.assertAlmostEqual(7.140413666e+01, data['radiance_dis'].sel(umu='-0.9', wvl='400', rad_wvl=400.120, rad_umu=-0.9).values[0])
        self.assertAlmostEqual(6.116877556e+00, data['radiance_dis'].sel(umu='-0.8', wvl='700', rad_wvl=700.158, rad_umu=-0.8).values[0])
        assert(np.sum(1-np.isnan(data['radiance_dis']))==16)
        npt.assert_almost_equal([np.nan], data['radiance_dis'].sel(umu='-0.8', wvl='600', rad_wvl=700.158, rad_umu=-0.8).values)
        sub.run(f'make -C test/integration/temp/ cleanall', shell=True)
    
    def test_disort_nktable(self):
        inifile='test/integration/fixtures/test_disort_nktable.ini'
        outfile='test/integration/temp/test_disort_nktable.nc'
        run(inifile)
        sub.run(f'make -C test/integration/temp/ cleanall', shell=True)
    def test_disort_ocean(self):
        result=np.genfromtxt('test/integration/fixtures/Ocean/Results.dat')
        inifile='test/integration/fixtures/Ocean/test_disort_ocean.ini'
        outfile='test/integration/temp/test_disort_ocean.nc'
        run(inifile)
        data=xr.open_dataset(outfile)
        data=data['standard_dis']
        data=data.squeeze()
        albedo=data.sel(quantity_dis='dis_eup')/(data.sel(quantity_dis='dis_edir')+data.sel(quantity_dis='dis_edn'))
        albedo=albedo.sel(rad_wvl=result[:,0])
        npt.assert_allclose(albedo, result[:,1])
        sub.run(f'make -C test/integration/temp/ cleanall', shell=True)

    def test_disort_wctau(self):
        inifile='test/integration/fixtures/Wctau/test_disort_wctau.ini'
        outfile='test/integration/temp/test_disort_wctau.nc'
        run(inifile)
        data=xr.open_dataset(outfile)
        data=data.squeeze()
        data=data.wctau_dis
        checkresult=np.array([[599.831543, 77.240723, 0.0], [600.453247, 77.242174, 1.4e-05], [600.80188, 77.24301, 3.2e-05], [601.435242, 77.244528, 5.5e-05], [602.335449, 77.246685, 8.7e-05], [602.585754, 77.247283, 9.2e-05], [603.195312, 77.248744, 0.00012], [603.859863, 77.250338, 0.000143], [604.22345, 77.251209, 0.000157], [604.929993, 77.252903, 0.00018], [605.525879, 77.254329, 0.000203], [606.12915, 77.255774, 0.00023], [606.623413, 77.256958, 0.000244], [607.052368, 77.257989, 0.000258], [607.692566, 77.259523, 0.000281], [608.317993, 77.261021, 0.000309], [608.830994, 77.262251, 0.000322], [609.294067, 77.263362, 0.000341], [609.871948, 77.264747, 0.000359]])
        npt.assert_almost_equal(data.rad_wvl, checkresult[:,0])
        npt.assert_almost_equal(data.sel(tau_type='scat'), checkresult[:,1])
        sub.run(f'make -C test/integration/temp/ cleanall', shell=True)


        

        
