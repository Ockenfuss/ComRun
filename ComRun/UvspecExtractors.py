import re
import numpy as np

class ResultNotFoundException(Exception): #Derived from Exception class
    def __init__(self, value): 
        self.value = value 
    def __str__(self): 
        return(repr(self.value)) 


def get_wctau_dis_fromstream(stream_verbose_stderr):
    """Get total water cloud optical thickness from disort verbose stderr output.

    Arguments:
        stream_verbose_stderr {stream} -- filestream of the stderr output.

    Raises:
        ResultNotFoundException: If no information was found.

    Returns:
        np 2darr -- columns wavelength, tau_scat, tau_abs
    """
    found=0
    result=[]
    for line in stream_verbose_stderr:
        #*** wavelength: iv = 0, 599.831543 nm
        if '*** wavelength: iv =' in line:
            match=re.search('([0-9]*\.[0-9]*) nm', line)
            wavelength=match.group(1)
        if not found and '*** optical_properties' in line:
            found=1
        if found and 'sum |' in line:
            arr=line.replace('|', ' ')
            arr=arr.split()
            found=0
            result.append([float(wavelength), float(arr[6]), float(arr[7])])
    if not result:
        raise ResultNotFoundException('No information about cloud optical thickness found!')
    return np.array(result)

def get_optprop_table_fromstream(stream_verbose_stderr):
    """Get water cloud optical thickness from disort verbose stderr output for every internal level.

    Arguments:
        stream_verbose_stderr {stream} -- filestream of the stderr output.

    Raises:
        ResultNotFoundException: If no information was found.

    Returns:
        np 2darr -- columns wavelength, tau_scat, tau_abs
    """
    found=0
    result={}
    table=[]
    for line in stream_verbose_stderr:
        #*** wavelength: iv = 0, 599.831543 nm
        if '*** wavelength: iv =' in line:
            match=re.search('([0-9]*\.[0-9]*) nm', line)
            wavelength=match.group(1)
        if not found and '*** optical_properties' in line:
            found=1
        if found and '---------------------------------------------' in line:
            found+=1
            continue
        if found==3:
            arr=line.replace('|', ' ')
            arr=arr.split()
            try:
                table.append([float(val) for val in arr])
            except ValueError:
                if 'The phase function' in line:
                    result[float(wavelength)]=np.array(table)
                    table=[]
                    found=0
                else:
                    raise Exception('Error: Did not find end of optprop table like expected.')
    return result


