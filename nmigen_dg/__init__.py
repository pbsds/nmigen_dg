# dogelang import hook
import dg

# hook into the nmigen 'get_src_loc' function
from . import tracer

# import the DSL
from .dsl import *

# cleanup the namespace
del dg, tracer, dsl

__version__ = "0.3.0"
