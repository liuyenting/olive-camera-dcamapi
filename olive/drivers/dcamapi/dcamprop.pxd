cdef extern from 'lib/dcamprop.h':
    ctypedef enum DCAMPROPOPTION:
        ##
        ## direction flag for dcam_getnextpropertyid(), dcam_querypropertyvalue()
        ##
        DCAMPROP_OPTION_PRIOR,	      # prior value
        DCAMPROP_OPTION_NEXT,	      # next value or id

        ##
        ## direction flag for dcam_querypropertyvalue()
        ##
        DCAMPROP_OPTION_NEAREST,	  # nearest value

        ##
        ## option for dcam_getnextpropertyid()
        ##
        DCAMPROP_OPTION_SUPPORT,	  # default option
        DCAMPROP_OPTION_UPDATED,	  # UPDATED and VOLATILE can be used at same time
        DCAMPROP_OPTION_VOLATILE,	  # UPDATED and VOLATILE can be used at same time
        DCAMPROP_OPTION_ARRAYELEMENT, # ARRAYELEMENT

        DCAMPROP_OPTION_NONE

    ctypedef enum DCAMPROPATTRIBUTE:
        ##
        ## supporting information of DCAM_PROPERTYATTR
        ##
        DCAMPROP_ATTR_HASRANGE		= 0x80000000,
        DCAMPROP_ATTR_HASSTEP		= 0x40000000,
        DCAMPROP_ATTR_HASDEFAULT	= 0x20000000,
        DCAMPROP_ATTR_HASVALUETEXT	= 0x10000000,

        ##
        ## property id information
        ##
        DCAMPROP_ATTR_HASCHANNEL	= 0x08000000,	# can set the value for each channels

        ##
        ## property attribute
        ##
        # NOTE
        #   dcam_setproperty() or dcam_setgetproperty() will fail if this bit exists
        DCAMPROP_ATTR_AUTOROUNDING	= 0x00800000,

        # NOTE
        #   value step of DCAM_PROPERTYATTR is not consistent across the entire range
        DCAMPROP_ATTR_STEPPING_INCONSISTENT = 0x00400000,

        DCAMPROP_ATTR_DATASTREAM	= 0x00200000,	# releated to image attribute

        DCAMPROP_ATTR_HASRATIO		= 0x00100000,	# value has ratio control capability

        DCAMPROP_ATTR_VOLATILE		= 0x00080000,	# value may be changed automatically

        DCAMPROP_ATTR_WRITABLE		= 0x00020000,	# value can be set when state is manual
        DCAMPROP_ATTR_READABLE		= 0x00010000,	# value is readable when state is manual

        DCAMPROP_ATTR_HASVIEW		= 0x00008000,	# value can set the value for each views

        DCAMPROP_ATTR_ACCESSREADY	= 0x00002000,	# This value can get or set at READY status
        DCAMPROP_ATTR_ACCESSBUSY	= 0x00001000,	# This value can get or set at BUSY status

        ##
        ## property value type
        ##
        # NOTE
        #   no single-precision float, double required even if the property is not REAL
        DCAMPROP_TYPE_NONE			= 0x00000000,	# undefined
        DCAMPROP_TYPE_MODE			= 0x00000001,	# 01:	mode, 32bit integer in case of 32bit OS
        DCAMPROP_TYPE_LONG			= 0x00000002,	# 02:	32bit integer in case of 32bit OS
        DCAMPROP_TYPE_REAL			= 0x00000003,	# 03:	64bit float

        DCAMPROP_TYPE_MASK			= 0x0000000F	# mask for property value type

    ctypedef enum DCAMPROPATTRIBUTE2:
        ##
        ## supporting information of DCAM_PROPERTYATTR
        ##
        DCAMPROP_ATTR2_ARRAYBASE	= 0x08000000,
        DCAMPROP_ATTR2_ARRAYELEMENT	= 0x04000000,

        DCAMPROP_ATTR2_REAL32		= 0x02000000,
        DCAMPROP_ATTR2_INITIALIZEIMPROPER = 0x00000001,

        DCAMPROP_ATTR2__FUTUREUSE	= 0x0007FFFC

    ctypedef enum DCAMPROPUNIT:
        DCAMPROP_UNIT_SECOND		= 1,
        DCAMPROP_UNIT_CELSIUS		= 2,
        DCAMPROP_UNIT_KELVIN		= 3,
        DCAMPROP_UNIT_METERPERSECOND= 4,
        DCAMPROP_UNIT_PERSECOND		= 5,
        DCAMPROP_UNIT_DEGREE		= 6,
        DCAMPROP_UNIT_MICROMETER	= 7,

        DCAMPROP_UNIT_NONE			= 0
