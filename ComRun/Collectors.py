import xarray as xr
import re as reg
import numpy as np
from ComRun.Helperfunctions import append_ids
import os


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
            temp=new.combine_first(self.data[new.name])# use combine_first because it allows for coordinate alignment and extends if necessary
            self.data=xr.merge([temp, self.data], compat='override')#now, merge the new data array in the full dataset

    def save_snapshot(self, savefile):
        self.data.to_netcdf(savefile)

    def load_existing(self, filename):
        new=xr.load_dataset(filename)
        if not np.all([c in new.coords for c in self.data.coords]):
            raise Exception(f'Not all necessary dimensions are present in {filename}!')
        self.data=new



    def save(self, savefile, inpLogger, templates=None):
        self.save_snapshot(savefile)
        inpLogger.add_outfile(savefile)
        logfile=os.path.splitext(savefile)[0]+".log"
        inpLogger.write_log(logfile, old_logs=templates)



class Collector(object):
    def __init__(self, stdout, stderr, infile, miscfiles, collection_keys, variables, tied=[]):
        self.stdoutbase=stdout
        self.stderrbase=stderr
        self.infilebase=infile
        self.miscfilesbase=miscfiles
        self.collection_keys=collection_keys
        self.output=Output(variables, tied)

    def open_file(self,filename):
        with open(filename, 'r') as file:
            data=file.read()
        return data

    def save(self, savefile, inpLogger, templates=None):
        self.output.save(savefile, inpLogger, templates)

class EmptyCollector(Collector):
    def __init__(self):
        super().__init__(None, None, None,None, None, {}, [])
    
    def collect(self, state, chunkid, taskid):
        pass
    
class UvspecCollector(Collector):
    def __init__(self, stdout, stderr, infile,miscfiles, collection_keys, variables, tied=[]):
        super().__init__(stdout, stderr, infile, miscfiles, collection_keys, variables, tied=[])
        self.extraction_functions={"time_all":self.get_time_all, "radiance": self.get_radiance, "photons_second": self.get_photons_second, "radiance_std": self.get_radiance_std, "radiance_dis": self.get_radiance_dis, "dis_std":self.get_dis_std, "mie_all":self.get_mie_std}


    def collect(self, cartesian_state, chunkid, taskid):
        self.stdoutfile=append_ids(self.stdoutbase, chunkid, taskid)
        self.stderrfile=append_ids(self.stderrbase, chunkid, taskid)
        self.miscfiles=[append_ids(f, chunkid, taskid) for f in self.miscfilesbase]
        self.infile=append_ids(self.infilebase,chunkid, taskid)
        for key in self.collection_keys:
            self.output.add_data(self.extraction_functions[key](), cartesian_state)

    def get_basename(self):
        """Get the parameter value of "mc_basename" in a uvspec input file
    
        Arguments:
            uvspec_input {str} -- The input you would pipe to uvspec stdin
        
        Returns:
            str -- the value of mc_basename
        """
        content=self.open_file(self.infile)
        basename=reg.findall(r"mc_basename [^\n]*", content)
        if len(basename)>0:
            basename=basename[-1]#last line
            return basename.split(" ")[1]#last word
        raise Exception(f"mc_basename not found in any of the files {self.infile}!")


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
        basename=self.get_basename()
        data=np.genfromtxt(basename+".rad.spc")
        data=np.atleast_2d(data)
        polarized=False
        if len(data)>1:
            if np.sum(data[0,:4]==data[1,:4])==4:#if the first two rows have equal coordinates, they represent different I,Q,U,V
                polarized=True
        rad_wvl=np.unique(data[:,0])
        rad_ix=np.unique(data[:,1])
        rad_iy=np.unique(data[:,2])
        rad_iz=np.unique(data[:,3])
        if polarized:
            rad_pol=['I', 'Q', 'U', 'V']
        else:
            rad_pol=['I']
        rad_space_shape=(len(rad_wvl), len(rad_ix), len(rad_iy), len(rad_iz), len(rad_pol))
        radiance=np.reshape(data[:,4], rad_space_shape)
        result=xr.DataArray(radiance, coords=[('rad_wvl', rad_wvl),('rad_ix', rad_ix),('rad_iy', rad_iy),('rad_iz', rad_iz),('rad_pol', rad_pol)])
        result.name='radiance'
        return result
        
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
        lines=stdout.split('\n')[:-1]
        data=[np.atleast_1d(np.fromstring(lines[i], sep=' ', dtype=float)) for i in range(len(lines))]
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
        """Read the seven standard output values from uvspec disort output"""
        stdout=self.open_file(self.stdoutfile)
        lines=stdout.split('\n')[:-1]
        data=[np.fromstring(lines[i], sep=' ', dtype=float) for i in range(len(lines))]
        assert(len(data[0])==7)#First line
        if len(data)<4 or len(data[0])==len(data[1])==len(data[2]):#no radiance
            n_wvl=len(data)-1
            headlines=range(n_wvl)#Indices of the standard output line of disort
        else:
            rad_phi=data[1]
            n_phi=len(rad_phi)
            if n_phi==7:
                print("Error: output not unique if 7 phi angles are specified!")
            assert(n_phi!=7)
            data_lengths=np.array([len(data[i]) for i in range(len(data))])
            philines=np.where(data_lengths==n_phi)[0]
            headlines=philines-1
            n_wvl=len(headlines)
        rad_wvl=[data[i][0] for i in headlines]

        dis_edir=np.zeros((n_wvl))
        dis_edn=np.zeros((n_wvl))
        dis_eup=np.zeros((n_wvl))
        dis_uavgdir=np.zeros((n_wvl))
        dis_uavgdn=np.zeros((n_wvl))
        dis_uavgup=np.zeros((n_wvl))

        for i in range(n_wvl):
            dis_edir[i]=data[headlines[i]][1]
            dis_edn[i]=data[headlines[i]][2]
            dis_eup[i]=data[headlines[i]][3]
            dis_uavgdir[i]=data[headlines[i]][4]
            dis_uavgdn[i]=data[headlines[i]][5]
            dis_uavgup[i]=data[headlines[i]][6]
        
        disort_output=np.row_stack((dis_edir, dis_edn, dis_eup, dis_uavgdir, dis_uavgdn, dis_uavgup))
        result=xr.DataArray(disort_output, coords=[('quantity_dis', ['dis_edir', 'dis_edn', 'dis_eup', 'dis_uavgdir', 'dis_uavgdn', 'dis_uavgup']),('rad_wvl', rad_wvl)])
        result.name='standard_dis'
        return result

        #Create dimension if necessary
        # if not ('rad_wvl' in output.dims):
        #     output.coords['rad_wvl']=('rad_wvl', rad_wvl)
        # #create DataArray if necessary
        # if not ('dis_edir' in output):
        #     dims=tuple(np.append(list(act_state.keys()), ['rad_wvl']))
        #     val_space_shape=tuple([output.dims[d] for d in dims])
        #     output['dis_edir']=(dims, np.zeros(val_space_shape))
        # output['dis_edir'][act_state]=dis_edir

        # if not ('dis_edn' in output):
        #     dims=tuple(np.append(list(act_state.keys()), ['rad_wvl']))
        #     val_space_shape=tuple([output.dims[d] for d in dims])
        #     output['dis_edn']=(dims, np.zeros(val_space_shape))
        # output['dis_edn'][act_state]=dis_edn

        # if not ('dis_eup' in output):
        #     dims=tuple(np.append(list(act_state.keys()), ['rad_wvl']))
        #     val_space_shape=tuple([output.dims[d] for d in dims])
        #     output['dis_eup']=(dims, np.zeros(val_space_shape))
        # output['dis_eup'][act_state]=dis_eup

        # if not ('dis_uavgdir' in output):
        #     dims=tuple(np.append(list(act_state.keys()), ['rad_wvl']))
        #     val_space_shape=tuple([output.dims[d] for d in dims])
        #     output['dis_uavgdir']=(dims, np.zeros(val_space_shape))
        # output['dis_uavgdir'][act_state]=dis_uavgdir

        # if not ('dis_uavgdn' in output):
        #     dims=tuple(np.append(list(act_state.keys()), ['rad_wvl']))
        #     val_space_shape=tuple([output.dims[d] for d in dims])
        #     output['dis_uavgdn']=(dims, np.zeros(val_space_shape))
        # output['dis_uavgdn'][act_state]=dis_uavgdn

        # if not ('dis_uavgup' in output):
        #     dims=tuple(np.append(list(act_state.keys()), ['rad_wvl']))
        #     val_space_shape=tuple([output.dims[d] for d in dims])
        #     output['dis_uavgup']=(dims, np.zeros(val_space_shape))
        # output['dis_uavgup'][act_state]=dis_uavgup

    def get_mie_std(self):
        pass
    

