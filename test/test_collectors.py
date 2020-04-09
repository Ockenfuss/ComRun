from ComRun.Collectors import Output
import xarray as xr
import numpy.testing as npt
import numpy as np
import unittest as ut

class OutputTest(ut.TestCase):
    def test_Output(self):
        variables={'state1':[1,2], 'state2':[10,20], 'state3':['a', 'b'], 'state4':['c','d'], 'state4':[1,2,3,4]}
        tied=[['state1', 'state3'], ['state4']]
        out=Output(variables, tied)
        self.assertCountEqual(out.data.dims, ['state1', 'state2', 'state4'])
        self.assertEqual(out.data['state3'].dims[0], 'state1')
    
    def test_add(self):
        variables={'state1':[1,2], 'state2':[3,4]}
        out=Output(variables)

        #Add new variable
        state={'state1':[1], 'state2':[4]}
        new=xr.DataArray([1,2], coords=[('wvl', [400,500])])
        new.name='radiance'
        out.add_data(new, state)
        self.assertTrue('radiance' in out.data.variables)
        npt.assert_array_equal(out.data['radiance'].sel(state1=1, state2=4, wvl=[400,500]).values, [1,2])

        #Update with a new state
        state2={'state1':[2], 'state2':[4]}
        new2=xr.DataArray([10,20], coords=[('wvl', [400,500])])
        new2.name='radiance'
        out.add_data(new2, state2)
        npt.assert_array_equal(out.data['radiance'].sel(state1=1, state2=4, wvl=[400,500]).values, [1,2])
        npt.assert_array_equal(out.data['radiance'].sel(state1=2, state2=4, wvl=[400,500]).values, [10,20])

        #Update with a new state that extends the dimensions
        state2={'state1':[2], 'state2':[4]}
        new2=xr.DataArray([30,40], coords=[('wvl', [2100,2200])])
        new2.name='radiance'
        out.add_data(new2, state2)
        npt.assert_array_equal(out.data['radiance'].sel(state1=1, state2=4, wvl=[400,500]).values, [1,2])
        npt.assert_array_equal(out.data['radiance'].sel(state1=2, state2=4, wvl=[400,500]).values, [10,20])
        npt.assert_array_equal(out.data['radiance'].sel(state1=2, state2=4, wvl=[2100,2200]).values, [30,40])
        npt.assert_array_equal(out.data['radiance'].sel(state1=1, state2=4, wvl=[2100,2200]).values, [np.nan,np.nan])

        #Update with an array that extends the dimensions partially
        state2={'state1':[1], 'state2':[4]}
        new2=xr.DataArray([0.1,0.2], coords=[('wvl', [500,3000])])
        new2.name='radiance'
        out.add_data(new2, state2)
        npt.assert_array_equal(out.data['radiance'].sel(state1=1, state2=4, wvl=[400,500]).values, [1,0.1])
        npt.assert_array_equal(out.data['radiance'].sel(state1=2, state2=4, wvl=[400,500]).values, [10,20])
        npt.assert_array_equal(out.data['radiance'].sel(state1=2, state2=4, wvl=[2100,2200]).values, [30,40])
        npt.assert_array_equal(out.data['radiance'].sel(state1=1, state2=4, wvl=[2100,3000]).values, [np.nan,0.2])
    def test_add_str(self):
        variables={'state1':["abc",'def'], 'state2':[3,4]}
        out=Output(variables)

        #Add new variable
        state={'state1':['abc'], 'state2':[4]}
        new=xr.DataArray(["a", "xyz"], coords=[('wvl', [400,500])])
        new.name='radiance'
        out.add_data(new, state)
        self.assertTrue('radiance' in out.data.variables)
        npt.assert_array_equal(out.data['radiance'].sel(state1='abc', state2=4, wvl=[400,500]).values, ['a','xyz'])
        #Update with an array that extends the dimensions partially
        state2={'state1':['abc'], 'state2':[4]}
        new2=xr.DataArray(['c', 'd'], coords=[('wvl', [500,3000])])
        new2.name='radiance'
        out.add_data(new2, state2)
        npt.assert_array_equal(out.data['radiance'].sel(state1='abc', state2=4, wvl=[400,500]).values, ['a','c'])
        npt.assert_array_equal(out.data['radiance'].sel(state1='abc', state2=4, wvl=[500,3000]).values, ['c','d'])

    def test_add_groups(self):
        variables={'state1':[1,2], 'state2':[3,4]}
        out=Output(variables, tied=[['state1', 'state2']])

        #Add new variable
        state={'state1':[1]}
        new=xr.DataArray([1,2], coords=[('wvl', [400,500])])
        new.name='radiance'
        out.add_data(new, state)
        self.assertCountEqual(list(out.data.coords), ['state1', 'state2', 'wvl'])
        self.assertCountEqual(list(out.data.dims), ['state1', 'wvl'])
        self.assertCountEqual(list(out.data['radiance'].dims), ['state1', 'wvl'])
