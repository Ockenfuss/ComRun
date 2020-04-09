import re as reg
import numpy as np
import xarray as xr
import subprocess

class UvspecError(Exception):
    """Exception raised for errors in uvspec.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class uvspec(object):
    def __init__(self, input):
        self.input=input
        self._uvspec_command=uvspec
        self._verbose='info'

    def get_basename(self):
        """Get the parameter value of "mc_basename" in a uvspec input file
    
        Arguments:
            uvspec_input {str} -- The input you would pipe to uvspec stdin
        
        Returns:
            str -- the value of mc_basename
        """
        basename=reg.findall(r"mc_basename [^\n]*", self.input)
        if len(basename)>0:
            basename=basename[-1]
        else:
            return ""
        return basename.split(" ")[1]


    def write_inputfile(self, filename=None):
        """Save the uvspec input in a file
        
        Arguments:
            filename {str} -- filename to write        
        """
        if filename:
            self._filename=filename
        filename=self._filename
        file=open(filename, "w")
        file.write(self.input)
        file.close()
    
    def write_output(self, stdoutfile=None, stderrfile=None):
        """Write stderr and stdout to file.
        
        Keyword Arguments:
            stdoutfile {str} -- If given, stdout is written to this file and the internal filename is updated. (default: {None})
            stderrfile {str} -- If given, stderr is written to this file and the internal filename is updated. (default: {None})
        """
        if stdoutfile:
            self._stdoutfile=stdoutfile
        stdoutfile=self._stdoutfile
        with open(stdoutfile, "w") as file:
            file.write(self.stdout)
        if stderrfile:
            self._stderrfile=stderrfile
        stderrfile=self._stderrfile
        with open(stderrfile, "w") as file:
            file.write(self.stderr)

    def open_output(self, stdoutfile=None, stderrfile=None):
        if stdoutfile:
            self._stdoutfile=stdoutfile
        stdoutfile=self._stdoutfile
        if stderrfile:
            self._stderrfile=stderrfile
        stderrfile=self._stderrfile
        with open(stdoutfile, "r") as file:
            self.stdout=file.read()
        with open(stderrfile, "r") as file:
            self.stderr=file.read()



    def execute(self):
        """Execute uvspec
        
        Arguments:
            uvspec_input {str} -- the string to be piped to uvspec as input
        
        Returns:
            (str, str) -- (stdout, stderr) as tuple of strings
        """
        uvspec=self._uvspec_command
        # process=subprocess.run(args=["time","-f", "\"Runtimes in total: %e %U %S\"", "ls"],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process=subprocess.Popen(args=["time","-f", "\"###Runtime %e %U %S ###\"", uvspec],stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf8')
        process.stdin.write(self.input)
        out,err=process.communicate()#also sends end signal to stdin?
        process.stdin.close()
        if self._info=="verbose":
            print(err)
            print(out)
        if process.returncode!=0:
            raise UvspecError("Error in uvspec: returncode was "+str(process.returncode))
            
        # print(process.stderr.decode('utf-8'))
        self.stdout=out
        self.stderr=err


    def process_output(self, key):
        extraction_functions={"time_all":get_time_all, "radiance": get_radiance, "photons_second": get_photons_second, "radiance_std": get_radiance_std, "radiance_dis": get_radiance_dis, "dis_std":get_dis_std, "mie_all":get_mie_std}
        return ()



    def get_time_all(self):
        #find values in output
        result=xr.DataArray(np.zeros(3), coords=[('rt_type', ['wall', 'user', 'kernel'])])
        m=reg.findall(r"###Runtime [^#]* ###", self.stderr)
        if len(m)!=0:
            m=m[0]
            m=np.array(m.split(" "))[1:4]
            m=m.astype(float)
        else:
            m=[np.nan, np.nan, np.nan]
        result.values=m
        return result
    

