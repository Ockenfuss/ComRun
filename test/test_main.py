import unittest as ut
import xarray as xr
import numpy as np
from ComRun.Main import Scheduler, TemplateHandler
import numpy.testing as npt
import itertools as it


class SchedulerTest(ut.TestCase):
    def test_generate_state(self):
        variables={'xval':['a', 'b', 'ccc'], 'y':['e', 'f']}
        sched=Scheduler(variables)
        states=list(sched.generate_state())
        solution=[{'xval': 'a', 'y': 'e'}, {'xval': 'a', 'y': 'f'}, {'xval': 'b', 'y': 'e'}, {'xval': 'b', 'y': 'f'}, {'xval': 'ccc', 'y': 'e'}, {'xval': 'ccc', 'y': 'f'}]
        self.assertCountEqual(states, solution)
    def test_generate_state_tied(self):
        variables={'x':['a', 'b', 'c'], 'y':['e', 'f'], 'z':['g','h']}
        tied=[['y', 'z']]
        sched=Scheduler(variables, tied)
        states=list(sched.generate_state())
        solution=[{'x': 'a', 'y': 'e', 'z': 'g'}, {'x': 'a', 'y': 'f', 'z': 'h'}, {'x': 'b', 'y': 'e', 'z': 'g'}, {'x': 'b', 'y': 'f', 'z': 'h'}, {'x': 'c', 'y': 'e', 'z': 'g'}, {'x': 'c', 'y': 'f', 'z': 'h'}]
        self.assertCountEqual(states, solution)
    def test_generate_state_multi(self):
        variables={'x':['a', 'b', 'c'], 'y':['e', 'f']}
        sched=Scheduler(variables)
        iter1=sched.generate_state()
        iter2=sched.generate_state()
        next(iter1)
        next(iter1)
        self.assertEqual(next(iter1),  {'x': 'b', 'y': 'e'})
        self.assertEqual(next(iter2),  {'x': 'a', 'y': 'e'})

# class TemplateHandlerTest(ut.TestCase):
#     def test_create(self):
        
