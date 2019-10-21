cdef extern from 'lib/dcamprop.h':
    ctypedef enum DCAMPROPOPTION:
        ## direction flag for dcam_getnextpropertyid(), dcam_querypropertyvalue()
        DCAMPROP_OPTION_PRIOR,	      # prior value
        DCAMPROP_OPTION_NEXT,	      # next value or id

        ## direction flag for dcam_querypropertyvalue()
        DCAMPROP_OPTION_NEAREST,	  # nearest value

        ## option for dcam_getnextpropertyid()
        DCAMPROP_OPTION_SUPPORT,	  # default option
        DCAMPROP_OPTION_UPDATED,	  # UPDATED and VOLATILE can be used at same time
        DCAMPROP_OPTION_VOLATILE,	  # UPDATED and VOLATILE can be used at same time
        DCAMPROP_OPTION_ARRAYELEMENT, # ARRAYELEMENT

        DCAMPROP_OPTION_NONE
