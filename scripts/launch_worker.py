#!/usr/bin/env python3
import os,sys
cpu=int(sys.argv[1]);fd=int(sys.argv[2]);os.sched_setaffinity(0,{cpu})
if fd>=0:
    assert os.read(fd,1)==b'1';os.close(fd)
os.execv(sys.argv[3],sys.argv[3:])
