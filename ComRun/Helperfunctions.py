import os



def append_ids(filename, chunkid=None, taskid=None):
        filename_ext=filename
        if chunkid is not None:
            base, ext=os.path.splitext(filename_ext)
            filename_ext=base+"_"+str(chunkid)+ext
        if taskid is not None:
            base, ext=os.path.splitext(filename_ext)
            filename_ext=base+"_"+str(taskid)+ext
        return filename_ext
