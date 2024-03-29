import xarray as xr
import sys
import numpy as np
import itertools as it
import jinja2 as jinja
import os as os
import subprocess
from ComRun.Helperfunctions import append_ids, consume
from ComRun.Collectors import UvspecCollector, EmptyCollector
from collections.abc import Iterable
import re
import time
VERSION="1.0.1"

class RunController(object):
    pass

class LocalRunner(RunController):
    def run(self, runfile):
        self.process=subprocess.Popen(f'chmod u=rwx {runfile}; {runfile}', shell=True)
    def wait(self):
        self.result=self.process.wait()

class SlurmRunner(RunController):
    def run(self, runfile):
        self.runfile=runfile
        subprocess.call(f'sbatch {runfile}', shell=True)
    
    def wait(self):
        waittime=30
        while(True):
            time.sleep(waittime)
            if self.finished():
                break
            # if waittime<600:
            #     waittime=int(waittime*1.5)

    def finished(self):
        filename=os.path.basename(self.runfile)
        uid=os.getuid()
        result=subprocess.run(f'squeue -u {uid} -n {filename} --format "%.5t"',stdout=subprocess.PIPE, shell=True)
        pattern = re.compile("\n[\s]*(R|PD)\n")
        if pattern.search(result.stdout.decode('utf-8')):
            return False
        return True

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
            state=dict(zip(allkeys, com))
            majorstate={k:state[k] for k in majorkeys}
            yield state, majorstate

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
        self.templates={}
        for i, tp in enumerate(temppaths):
            if tp:
                self.templates[names[i]]=Template.fromFilepath(tp, savepaths[i])
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

class EmptyHandler(TemplateHandler):
    def __init__(self):
        super().__init__([],[])
    def add_template(self, temppath, savepath, name=None):
        raise Exception('Not possible to add template to EmptyHandler object!')
def exe(command):
    proc=subprocess.Popen(command, shell=True)
    proc.wait()
def main():
    from inlog import Input as InputLogger
    import argparse
    par=argparse.ArgumentParser()
    par.add_argument('infile')
    args=par.parse_args()
    def_opts={}
    def_opts["Options"]={"idnumber":str(int(np.random.rand()*1e10)), "uvspec":"uvspec", "sep":",", "not_cartesian":"", "mode":"local","misctemplates":'',"miscfiles":"","info":"info", "chunkstart":"0","chunksize":"1", "append":"False"}
    inp=InputLogger.Input(args.infile,version=VERSION, def_opts=def_opts)
    inp.convert_array(str, "misctemplates", "Options", removeSpaces=True)
    inp.convert_array(str, "miscfiles", "Options", removeSpaces=True)
    inp.convert_array(str, "out_values","Output", removeSpaces=True)
    inp.convert_array(str, "not_cartesian", "Options", removeSpaces=True)
    inp.convert_type(int, 'chunksize', 'Options')
    inp.convert_type(int, 'chunkstart', 'Options')
    inp.convert_type(bool, 'append', 'Options')
    infodict={'quiet':0, 'info':1, 'verbose':2}
    info=infodict[inp.get('info', 'Options')]
    if info >0:
        inp.show_data()
    variables={}
    for var in inp.listKeys("Variables"):
        inp.convert_array(str, var,section="Variables", removeSpaces=False, sep=inp.get("sep", 'Options'))
        variables[var]=inp.get(var, "Variables")
    tied=[inp.get("not_cartesian",'Options')]
    if not inp.get("not_cartesian",'Options'):
        tied=[]
    runstate=inp.options['Run']
    outputfile=inp.get('outputfile', 'Options')
    chunksize=inp.get('chunksize', 'Options')
    chunkstart=inp.get('chunkstart', 'Options')

    mode=inp.get('mode', 'Options')
    misctemplates=inp.get('misctemplates', 'Options')
    intemplate=inp.get('intemplate', 'Options')
    template_handler=TemplateHandler(misctemplates, inp.get('miscfiles', 'Options'))
    template_handler.add_template(intemplate, inp.get('inputfile', 'Options'), 'input')
    runtemplate_handler=TemplateHandler(inp.get('runtemplate', 'Options'), inp.get('runfile', 'Options'), 'Run')
    if mode=='local':
        runner=LocalRunner()
        collector=UvspecCollector(inp.get("stdout", 'Options'), inp.get("stderr", 'Options'), inp.get("inputfile", 'Options'),inp.get("miscfiles", 'Options'), inp.get("out_values", 'Output'), variables, tied)
        if chunksize!=1:
            print("Warning: When running local, you probably want to set the chunksize to 1.")
    elif mode=='create':
        runner=EmptyRunner()
        collector=EmptyCollector()
    elif mode=='slurm':
        runner=SlurmRunner()
        collector=UvspecCollector(inp.get("stdout", 'Options'), inp.get("stderr", 'Options'), inp.get("inputfile", 'Options'),inp.get("miscfiles", 'Options'), inp.get("out_values", 'Output'), variables, tied)
    elif mode=='read':
        template_handler=EmptyHandler()
        runner=EmptyRunner()
        collector=UvspecCollector(inp.get("stdout", 'Options'), inp.get("stderr", 'Options'), inp.get("inputfile", 'Options'),inp.get("miscfiles", 'Options'), inp.get("out_values", 'Output'), variables, tied)
    else:
        raise KeyError(f'{mode} not a valid keyword for "mode"!')
    
    if inp.get('append', 'Options'):
        collector.output.load_existing(outputfile)

    scheduler=Scheduler(variables, tied)
    chunks_remaining=True
    states_creation=scheduler.generate_state()
    states_reading=scheduler.generate_state()
    chunkid=chunkstart
    consume(states_creation, chunksize*chunkstart)
    consume(states_reading, chunksize*chunkstart)
    while chunks_remaining:
        taskid=0
        while taskid<chunksize:
            try:
                state, _=next(states_creation)
            except StopIteration:
                chunks_remaining=False
                break
            template_handler.create(state,chunkid=chunkid, taskid=taskid)
            taskid+=1
            if info>1:
                print(f'Current state is {state}')
        if taskid==0 and not chunks_remaining:
            break
        runstate['jobs']=str(taskid-1)
        runfile=runtemplate_handler.create(runstate, chunkid=chunkid)[0]
        if info>0:
            print(f'Running chunk {chunkid} with {taskid} jobs')
        runner.run(runfile)
        runner.wait()
        taskid=0
        if info>0:
            print('Reading output...')
        while taskid<chunksize:
            try:
                _, majorstate=next(states_reading)
            except StopIteration:
                chunks_remaining=False
                break
            collector.collect(majorstate, chunkid, taskid)
            taskid+=1
            if info>1:
                print(f'Current state is {majorstate}')
        collector.save_snapshot(outputfile)
        if mode=='local' or mode=='slurm':
            exe(inp.get("clean",'Options'))
        chunkid+=1
    collector.save(outputfile, inp, [intemplate]+misctemplates)
    print(collector.output.data)
        # if chunkid==2:
        #     sys.exit()





if __name__=="__main__":
    main()






