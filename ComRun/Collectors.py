import xarray as xr
import re as reg
import numpy as np
from ComRun.Helperfunctions import append_ids


class Output(object):
    def __init__(self, variables, tied=[]):
        """Create an object around an xarray dataset, which is able to contain the simulation output.
        
        Arguments:
            object {Output} -- self
            variables {dict} -- The state space to explore in the form {variable:values, ...}
            tied {arr} -- Groups of coordinates which are tied together in the form [[var1, var2], [var3, ...]...]. Groups must be disjunct.
        """
        output=xr.Dataset()
        tied_flat=[i for group in tied for i in group]
        untied=[key for key in variables.keys() if key not in tied_flat]
        for var in untied:
            output.coords[var]=(var, variables[var])
        for group in tied:
            for var in group:
                output.coords[var]=(group[0], variables[var])
        self.data=output

    def add_data(self, new, state):
        """Add a new DataArray to the output. Existing values with matching coordinates are overwritten, non-existing coordinates are appended and nan's are introduced when necessary.
        
        Arguments:
            new {xr.DataArray} -- New data to be added.
            state {dict} -- The position in the output data where 'new' will be added.
        """
        lstate={key:[val] for i, (key, val) in enumerate(state.items())}
        new=new.expand_dims(lstate)
        if not new.name in self.data:
            self.data[new.name]=new
        else:
            self.data=new.combine_first(self.data)


class Collector(object):
    def __init__(self, stdout, stderr, infiles, collection_keys, variables, tied=[]):
        self.stdoutbase=stdout
        self.stderrbase=stderr
        self.infilesbase=infiles
        self.collection_keys=collection_keys
        self.output=Output(variables, tied)

    def open_file(self,filename):
        with open(filename, 'r') as file:
            data=file.read()
        return data

class EmptyCollector(Collector):
    def __init__(self):
        super().__init__(None, None, None, None, {}, [])
    
    def collect(self, state, chunkid, taskid):
        pass
    
class UvspecCollector(Collector):
    def __init__(self, stdout, stderr, infiles, collection_keys, variables, tied=[]):
        super().__init__(stdout, stderr, infiles, collection_keys, variables, tied=[])
        self.extraction_functions={"time_all":self.get_time_all, "radiance": self.get_radiance, "photons_second": self.get_photons_second, "radiance_std": self.get_radiance_std, "radiance_dis": self.get_radiance_dis, "dis_std":self.get_dis_std, "mie_all":self.get_mie_std}


    def collect(self, state, chunkid, taskid):
        self.stdoutfile=append_ids(self.stdoutbase, chunkid, taskid)
        self.stderrfile=append_ids(self.stderrbase, chunkid, taskid)
        self.infiles=[append_ids(f, chunkid, taskid) for f in self.infilesbase]
        for key in self.collection_keys:
            self.output.add_data(self.extraction_functions[key](), state)

    def get_basename(self):
        """Get the parameter value of "mc_basename" in a uvspec input file
    
        Arguments:
            uvspec_input {str} -- The input you would pipe to uvspec stdin
        
        Returns:
            str -- the value of mc_basename
        """
        for infile in self.infiles:
            content=self.open_file(infile)
            basename=reg.findall(r"mc_basename [^\n]*", content)
            if len(basename)>0:
                basename=basename[-1]#last line
                return basename.split(" ")[1]#last word
            else:
                continue
        raise Exception(f"mc_basename not found in any of the files {self.infiles}!")


    def get_time_all(self):
        stderr=self.open_file(self.stderrfile)
        #find values in output
        result=xr.DataArray(np.zeros(3), coords=[('rt_type', ['wall', 'user', 'kernel'])])
        result.name='time_all'
        m=reg.findall(r"###Runtime [^#]* ###", stderr)
        if len(m)!=0:
            m=m[0]
            m=np.array(m.split(" "))[1:4]
            m=m.astype(float)
        else:
            m=[np.nan, np.nan, np.nan]
        result.values=m
        return result

    def get_radiance(self):
        pass
    def get_photons_second(self):
        pass
    def get_radiance_std(self):
        pass
    def get_radiance_dis(self):
        """Read radiance for the case of 'disort', which prints it to stdout rather than a .rad.spc file.
        """
        #The output from disort is quite hard to read. The format is:
        #headline (length 7)
        #philine (length nphi)
        #multiple umu lines (length nphi+2)
        #headline
        #...
        #The strategy is to locate the philines and derive the structure of the rest from these points
        stdout=self.open_file(self.stdoutfile)
        lines=stdout.split('\n')
        data=[np.fromstring(lines[i], sep=' ', dtype=float) for i in range(len(lines))]
        rad_phi=data[1]
        n_phi=len(rad_phi)
        if n_phi==7:
            print("Error: output not unique if 7 phi angles are specified!")
        assert(n_phi!=7)
        assert(len(data[0])==7)#First line
        data_lengths=np.array([len(data[i]) for i in range(len(data))])
        philines=np.where(data_lengths==n_phi)[0]
        rad_wvl=[data[i-1][0] for i in philines]
        n_wvl=len(rad_wvl)
        n_umu=len(data)-2 if len(philines)==1 else philines[1]-philines[0]-2
        rad_umu=[data[philines[0]+i+1][0] for i in range(n_umu)]
        radiance_dis=np.zeros((n_wvl, n_umu, n_phi))
        for i in range(n_wvl):
            for j in range(n_umu):
                radiance_dis[i][j]=data[philines[i]+1+j][2:]

        result=xr.DataArray(radiance_dis, coords=[('rad_wvl', rad_wvl),('rad_umu', rad_umu),('rad_phi', rad_phi)])
        result.name='radiance_dis'
        return result

    def get_dis_std(self):
        pass
    def get_mie_std(self):
        pass
    

