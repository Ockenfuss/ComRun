import xarray as xr
import sys
import numpy as np
import itertools as it
import jinja2 as jinja
import os as os
import subprocess
from ComRun.Helperfunctions import append_ids
from ComRun.Collectors import UvspecCollector, EmptyCollector
from collections import Iterable

VERSION="1.0.0"

class RunController(object):
    pass

class LocalRunner(RunController):
    def run(self, runfile):
        self.process=subprocess.Popen(f'chmod u=rwx {runfile}; {runfile}', shell=True)
    def wait(self):
        self.result=self.process.wait()

class SlurmRunner(RunController):
    pass

class EmptyRunner(RunController):
    def run(self, *args, **kwargs):
        pass
    def wait(self):
        pass


class Scheduler(object):
    def __init__(self, variables, tied=[]):
        self.variables=variables
        self.tied=tied
    
    @classmethod
    def nflatten(cls,nestlist):
        for i in nestlist:
            if isinstance(i, Iterable) and not isinstance(i, str):
                for subc in cls.nflatten(i):
                    yield subc
            else:
                yield i

    def generate_state(self):
        """Generate an iterable over all possible states.
        
        Yields:
            dict -- A state in the form {key:value, key2:value2, ...}
        """
        #tied: [[y,z]]
        tied_flat=[i for group in self.tied for i in group]#[y,z]
        untied=[key for key in self.variables.keys() if key not in tied_flat]#[x]
        allkeys=untied+tied_flat#[x,y,z]
        majorkeys=untied+[group[0] for group in self.tied if group]#[x,y]
        iterables=[self.variables[v] for v in untied]+[zip( *[self.variables[v] for v in group]) for group in self.tied]#generate a combined iterable for all tied variables 
        for com in it.product(*iterables):
            com=Scheduler.nflatten(com)#Resolve the tuples from the combined iterables
            yield dict(zip(allkeys, com))

class Template(object):
    def __init__(self, templatefile, savepath):
        self.template=jinja.Template(templatefile.read())
        self.savepath=savepath
    
    @classmethod
    def fromFilepath(cls, templatepath, savepath):
        with open(templatepath) as f:
            return cls(f, savepath)
    
    def create(self, state, chunkid=None, taskid=None):
        state_interp=state.copy()
        if taskid is not None:
            state_interp={key:val.replace("TASKID", str(taskid)) for i, (key, val) in enumerate(state_interp.items())}
        if chunkid is not None:
            state_interp={key:val.replace("CHUNKID", str(chunkid)) for i, (key, val) in enumerate(state_interp.items())}
        filled=self.template.render(var=state_interp)
        savepath_ext=append_ids(self.savepath, chunkid, taskid)
        self.save_file(filled, savepath_ext)
        return savepath_ext


    
    def save_file(self, string, filename, accessmode="w"):
        """Save a string in a file
        
        Arguments:
            string {str} -- the string to save
            filename {str} -- filename to write
        
        Keyword Arguments:
            accessmode {str} -- access mode (write, append) (default: {"w"})
        """
        file=open(filename, accessmode)
        file.write(string)
        file.close()


class TemplateHandler(object):
    def __init__(self, temppaths, savepaths, names=None):
        temppaths=np.atleast_1d(temppaths)
        savepaths=np.atleast_1d(savepaths)
        assert(len(temppaths)==len(savepaths))
        if not names:
            names=np.arange(len(temppaths))
        self.templates={names[i]:Template.fromFilepath(tp,savepaths[i]) for i, tp in enumerate(temppaths)}
        self.counter=len(self.templates)

    def create(self, state, names=None, chunkid=None, taskid=None):
        if names is None:
            names=self.templates.keys()
        runfiles=[]
        for n in names:
            runfiles.append(self.templates[n].create(state, chunkid=chunkid, taskid=taskid))
        return runfiles

    def add_template(self, temppath, savepath, name=None):
        if not name:
            name=self.counter
        self.templates[name]=Template.fromFilepath(temppath, savepath)
        self.counter+=1

def main():
    from MyPython import Input as InputLogger
    import argparse
    par=argparse.ArgumentParser()
    par.add_argument('infile')
    args=par.parse_args()
    def_opts={}
    def_opts["Options"]={"idnumber":str(int(np.random.rand()*1e10)), "uvspec":"uvspec", "sep":",", "not_cartesian":"", "mode":"local","misctemplate":"","miscfiles":"","info":"info", "slurmtemplate":"/project/meteo/work/Paul.Ockenfuss/Master/Simulation/Sourcecode/Tools/Templates/Slurm_Input_template.template"}
    inp=InputLogger.Input(args.infile,version=VERSION, def_opts=def_opts)
    inp.convert_array(str, "misctemplate", "Options", removeSpaces=True)
    inp.convert_array(str, "miscfiles", "Options", removeSpaces=True)
    inp.convert_array(str, "out_values","Output", removeSpaces=True)
    inp.convert_array(str, "not_cartesian", "Options", removeSpaces=True)
    inp.convert_type(int, 'chunksize', 'Options')

    variables={}
    for var in inp.listKeys("Variables"):
        inp.convert_array(str, var,section="Variables", removeSpaces=False, sep=inp.get("sep", 'Options'))
        variables[var]=inp.get(var, "Variables")
    tied=[inp.get("not_cartesian",'Options')]
    if inp.get("not_cartesian",'Options')[0]=="":
        tied=[]
    runstate=inp.options['Run']


    mode=inp.get('mode', 'Options')
    template_handler=TemplateHandler(inp.get('templates', 'Options'), inp.get('inputfiles', 'Options'))
    runtemplate_handler=TemplateHandler(inp.get('runtemplate', 'Options'), inp.get('runfile', 'Options'), 'Run')
    if mode=='local':
        runner=LocalRunner()
        collector=UvspecCollector(inp.get("stdout", 'Options'), inp.get("stderr", 'Options'), inp.get("inputfiles", 'Options'), inp.get("out_values", 'Output'), variables, tied)
    elif mode=='create':
        runner=EmptyRunner()
        collector=EmptyCollector()
    elif mode=='slurm':
        runner=SlurmRunner()
    elif mode=='read':
        runner=EmptyRunner()
        collector=EmptyCollector()
    
    scheduler=Scheduler(variables, tied)
    chunks_remaining=True
    chunkid=0
    chunksize=inp.get('chunksize', 'Options')
    states_creation=scheduler.generate_state()
    states_reading=scheduler.generate_state()
    while chunks_remaining:
        taskid=0
        while taskid<chunksize:
            try:
                state=next(states_creation)
            except StopIteration:
                chunks_remaining=False
                break
            template_handler.create(state,chunkid=chunkid, taskid=taskid)
            taskid+=1
        if taskid==0 and not chunks_remaining:
            break
        runstate['jobs']=str(taskid)
        runfile=runtemplate_handler.create(runstate, chunkid=chunkid)[0]
        runner.run(runfile)
        runner.wait()
        taskid=0
        while taskid<chunksize:
            try:
                state=next(states_reading)
                print(state)
            except StopIteration:
                chunks_remaining=False
                break
            collector.collect(state, chunkid, taskid)
            taskid+=1
        chunkid+=1
    print(collector.output.data)





if __name__=="__main__":
    main()






