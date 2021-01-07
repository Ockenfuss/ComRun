ComRun: A python module to explore a specific parameter space of a simulation.
# Introduction

If often occurs, that you have a computer simulation and want to explore its behaviour for all combinations of certain parameters. E.g., calculate the solar radiance at 5 different latitudes, for 10 different heights and 10 different surface types. This is what ComRun ("Combination Runner") is for. The program:
* Forms the **cartesian product** over the input parameters to create a set of possible input **states**
* Creates Inputfiles for every input state
* Starts the simulations
* Collects the results in a Netcdf file

Although I used ComRun primarily together with 'uvspec' from the libRadtran radiative transfer library, the module is generic and should be applicable to any other simulation software as well.

# Program flow
In the example from the introduction, we have $5*10*10=500$ different input states, which correspond to 500 simulation **tasks** to be performed. In general, we group these tasks into bigger **chunks** and perform the following steps repeatedly for every chunk.
## Input creation
All interaction with the simulation is via textfiles. Their name templates must be specified by the user and they get extended in the form `Filename_CHUNKID_TASKID.extension`, where `CHUNKID` and `TASKID` are two numbers.
At first, input files are created for every input state. Therefore, an input template file must be specified. The python template engine JINJA is used to replace all state variables (height, latitude) in the form `{{var.height}}`, `{{var.latitude}}` with their values.

## Running the simulation
The user must provide another JINJA template for a bash script. From this template, the program must be able to create a bash script, which runs all tasks in the current chunk.

## Collecting the results
In order for ComRun to read arbitrary simulation output, the user must provide functions which read the required quantity and return it as an xarray DataArray. Inside these functions, the name of the inputfile and filenames containing stdout and stderr are provided. ComRun calls these functions for every task in the current chunk and merges the returned arrays together.

# Input Description
ComRun is controlled by an .ini file, which is read using the python configparser module.
```ini
###This section contains all input options for ComRun
[Options] 

#ComRun can operate in four modes:
#create: Create all the inputfiles, but do not execute the runscript or try to collect any results
#read: Try to collect all results, but do not execute the runscript or create any inputfiles
#local: Create inputfiles, execute the runscript in a subprocess, and collect results
#slurm: Create inputfiles, execute the runscript with the command 'sbatch', regularly check its status using 'squeue' and collect the results once 'sbatch' finished.
mode=local

#The file with the input template.
intemplate=Path/To/Input.template

#Optionally, additional templates can be specified
misctemplates=${fixtures}test_disort_nktable_wc.template

#The file with the template to start the simulation
runtemplate=Path/To/Run.template

#The filled templates will be stored here. The names will be extended in the form Path/Name_CHUNKID_TASKID.extension
inputfile=Path/Run${Options:idnumber}.inp
runfile=Path/Run${Options:idnumber}.sh
miscfiles=Path/Runwc.dat

#ComRun expects the standard output and standard error of each task to be in these folders, where the filenames are extended with CHUNKID and TASKID.
stdout=Path/Run${Options:idnumber}_stdout.dat
stderr=Path/Run${Options:idnumber}_stderr.dat


#The following command will be executed after all simulations in a chunk are finished
clean=make -C Path/To/Files/ cleanrun --quiet

#The final netcdf output file, containing the quantities specified in the "Output" section
outputfile=Path/Output.nc

#If true, 'outputfile' is read into memory in the beginning and extended with the collected output. Existing values might be overwritten if new values are found!
append=False

#This option is for convenience and can be used in the other options to ensure unique filenames for every run. If not set, a 10 digit random number is generated for each ComRun-call.
idnumber=324789

#separator used to separate parameter values in the Variables section. Default is ','
sep=,

#these parameters are varied together, i.e. no cartesian product is formed between them.
#Therefore, they all must have the same number of values in the Variables-section!
not_cartesian=umu, phi, sza, state

#How much information to print to stdout while running. Possible are quiet, info or verbose.
info=info

#Maximum number of tasks in each chunk.
chunksize=1

#Start with this chunk and omit the ones before
chunkstart=0

###Section with the parameters which are inserted in the input template#######
[Variables]
#Parameter names and values can be arbitraty alphanumeric strings.
#For the values, TASKID and CHUNKID are special terms which are replaced by the task and chunk number before being inserted in the template files
wvl_range=620 660, 2100 2200
umu=1.0
phi=0
sza=30
state=_CHUNKID_TASKID
lwc=0.1, 0.2
reff=10,12

###Section with the parameters which are inserted in the program execution file. It is expected that this file runs all tasks in one chunk
[Run]
#CHUNKID is replaced by the chunknumber
#Additionally, the parameter 'tasks' (number of tasks in chunk) is provided automatically
chunk=CHUNKID

#Usually, you want to have the names you specified in the Options section also to be available in your runscript
inputfile=${Options:inputfile}
stderr=${Options:stderr}
stdout=${Options:stdout}



###Section which specifies the desired output variables. These are keywords to specify which of the custom output functions should be called in this run, to collect the simulation output.
[Output]
out_values=time_all, radiance_dis
#For 'uvspec', the following collector functions are implemented: "time_all" "radiance" "photons_second" "radiance_std" "radiance_dis" "dis_std" "mie_all" "wctau_dis" "optprop_dis"
```