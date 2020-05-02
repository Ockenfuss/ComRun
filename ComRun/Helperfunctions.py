import os
import collections
import itertools as it


def append_ids(filename, chunkid=None, taskid=None):
        filename_ext=filename
        if chunkid is not None:
            base, ext=os.path.splitext(filename_ext)
            filename_ext=base+"_"+str(chunkid)+ext
        if taskid is not None:
            base, ext=os.path.splitext(filename_ext)
            filename_ext=base+"_"+str(taskid)+ext
        return filename_ext

def consume(iterator, n=None):
    "Advance the iterator n-steps ahead. If n is None, consume entirely."
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        collections.deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(it.islice(iterator, n, n), None)