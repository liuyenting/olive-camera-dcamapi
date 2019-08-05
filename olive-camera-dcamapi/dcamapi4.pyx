cimport cython

cdef extern from 'lib/dcamapi4.h':
    ctypedef void* HDCAM

    enum DCAMERR:
        ## 
        # status error 
        ##
        #: API cannot process in busy state
        DCAMERR_BUSY				= 0x80000101,
        #: API requires ready state
        DCAMERR_NOTREADY			= 0x80000103,
        #: API requires stable or unstable state
        DCAMERR_NOTSTABLE			= 0x80000104,
        #: API requires stable or unstable state
        DCAMERR_UNSTABLE			= 0x80000105,
        #: API requires busy state
        DCAMERR_NOTBUSY				= 0x80000107,
        
        #: some resource is exclusive and already used
        DCAMERR_EXCLUDED			= 0x80000110,
        
        #: something happens near cooler
        DCAMERR_COOLINGTROUBLE		= 0x80000302,
        #: no trigger when necessary. Some camera supports this error
        DCAMERR_NOTRIGGER			= 0x80000303,
        #: camera warns its temperature
        DCAMERR_TEMPERATURE_TROUBLE = 0x80000304,
        #: input too frequent trigger. Some camera supports this error
        DCAMERR_TOOFREQUENTTRIGGER	= 0x80000305,

        
        ##
        # wait error 
        ##
        #: abort process
        DCAMERR_ABORT				= 0x80000102,
        #: timeout
        DCAMERR_TIMEOUT				= 0x80000106,
        #: frame data is lost
        DCAMERR_LOSTFRAME			= 0x80000301,
        #: frame is lost but reason is low level driver's bug
        DCAMERR_MISSINGFRAME_TROUBLE= 0x80000f06,
        #: hpk format data is invalid data
        DCAMERR_INVALIDIMAGE		= 0x80000321,
        
        ##
        # initialization error
        ##
        #: not enough resource except memory
        DCAMERR_NORESOURCE			= 0x80000201,
        #: not enough memory
        DCAMERR_NOMEMORY			= 0x80000203,
        #: no sub module
        DCAMERR_NOMODULE			= 0x80000204,
        #: no driver
        DCAMERR_NODRIVER			= 0x80000205,
        #: no camera
        DCAMERR_NOCAMERA			= 0x80000206,
        #: no grabber 
        DCAMERR_NOGRABBER			= 0x80000207,
        #: no combination on registry
        DCAMERR_NOCOMBINATION		= 0x80000208,

        #: DEPRECATED
        DCAMERR_FAILOPEN			= 0x80001001,
        #: dcam_init() found invalid module
        DCAMERR_INVALIDMODULE		= 0x80000211,
        #: invalid serial port
        DCAMERR_INVALIDCOMMPORT		= 0x80000212,
        #: the bus or driver are not available
        DCAMERR_FAILOPENBUS			= 0x81001001,
        #: camera report error during opening
        DCAMERR_FAILOPENCAMERA		= 0x82001001,
        #: need to update frame grabber firmware to use the camera
        DCAMERR_FRAMEGRABBER_NEEDS_FIRMWAREUPDATE = 0x80001002,
        
        ##
        # calling error 
        ##
        #: invalid camera
        DCAMERR_INVALIDCAMERA		= 0x80000806,
        #: invalid camera handle
        DCAMERR_INVALIDHANDLE		= 0x80000807,
        #: invalid parameter
        DCAMERR_INVALIDPARAM		= 0x80000808,
        #: invalid property value
        DCAMERR_INVALIDVALUE		= 0x80000821,
        #: value is out of range
        DCAMERR_OUTOFRANGE			= 0x80000822,
        #: the property is not writable
        DCAMERR_NOTWRITABLE			= 0x80000823,
        #: the property is not readable
        DCAMERR_NOTREADABLE			= 0x80000824,
        #: the property id is invalid
        DCAMERR_INVALIDPROPERTYID	= 0x80000825,
        #: old API cannot present the value because only new API need to be used
        DCAMERR_NEWAPIREQUIRED		= 0x80000826,
        #: this error happens DCAM get error code from camera unexpectedly
        DCAMERR_WRONGHANDSHAKE		= 0x80000827,
        #: there is no altenative or influence id, or no more property id
        DCAMERR_NOPROPERTY			= 0x80000828,
        #: the property id specifies channel but channel is invalid
        DCAMERR_INVALIDCHANNEL		= 0x80000829,
        #: the property id specifies channel but channel is invalid
        DCAMERR_INVALIDVIEW			= 0x8000082a,
        #: the combination of subarray values are invalid. e.g. DCAM_IDPROP_SUBARRAYHPOS + DCAM_IDPROP_SUBARRAYHSIZE is greater than the number of horizontal pixel of sensor
        DCAMERR_INVALIDSUBARRAY		= 0x8000082b,
        #: 
        DCAMERR_ACCESSDENY			= 0x8000082c,##			##
        #: 
        DCAMERR_NOVALUETEXT			= 0x8000082d,##		the property does not have value text	##
        #: 
        DCAMERR_WRONGPROPERTYVALUE	= 0x8000082e,##		at least one property value is wrong	##
        #: 
        DCAMERR_DISHARMONY			= 0x80000830,##		the paired camera does not have same parameter	##
        #: 
        DCAMERR_FRAMEBUNDLESHOULDBEOFF=0x80000832,##	framebundle mode should be OFF under current property settings	##
        #: 
        DCAMERR_INVALIDFRAMEINDEX	= 0x80000833,##		the frame index is invalid	##
        #: 
        DCAMERR_INVALIDSESSIONINDEX	= 0x80000834,##		the session index is invalid	##
        #: 
        DCAMERR_NOCORRECTIONDATA	= 0x80000838,##		not take the dark and shading correction data yet.	##
        #: 
        DCAMERR_CHANNELDEPENDENTVALUE= 0x80000839,##	each channel has own property value so can't return overall property value.	##
        #: 
        DCAMERR_VIEWDEPENDENTVALUE	= 0x8000083a,##		each view has own property value so can't return overall property value.	##
        #: 
        DCAMERR_INVALIDCALIBSETTING	= 0x8000083e,##		the setting of properties are invalid on sampling calibration data. some camera has the limitation to make calibration data. e.g. the trigger source is INTERNAL only and read out direction isn't trigger.	##
        #: 
        DCAMERR_LESSSYSTEMMEMORY	= 0x8000083f,##		the sysmte memory size is too small. PC doesn't have enough memory or is limited memory by 32bit OS.	##
        #: 
        DCAMERR_NOTSUPPORT			= 0x80000f03,##		camera does not support the function or property with current settings	##

        ## camera or bus trouble ##
        DCAMERR_FAILREADCAMERA		= 0x83001002,##		failed to read data from camera	##
        DCAMERR_FAILWRITECAMERA		= 0x83001003,##		failed to write data to the camera	##
        DCAMERR_CONFLICTCOMMPORT	= 0x83001004,##		conflict the com port name user set	##
        DCAMERR_OPTICS_UNPLUGGED	= 0x83001005,## 	Optics part is unplugged so please check it.	##
        DCAMERR_FAILCALIBRATION		= 0x83001006,##		fail calibration	##

        ## 0x84000100 - 0x840001FF, DCAMERR_INVALIDMEMBER_x ##
        DCAMERR_INVALIDMEMBER_3		= 0x84000103,##		3th member variable is invalid value	##
        DCAMERR_INVALIDMEMBER_5		= 0x84000105,##		5th member variable is invalid value	##
        DCAMERR_INVALIDMEMBER_7		= 0x84000107,##		7th member variable is invalid value	##
        DCAMERR_INVALIDMEMBER_8		= 0x84000108,##		7th member variable is invalid value	##
        DCAMERR_INVALIDMEMBER_9		= 0x84000109,##		9th member variable is invalid value	##
        DCAMERR_FAILEDOPENRECFILE	= 0x84001001,##		DCAMREC failed to open the file	##
        DCAMERR_INVALIDRECHANDLE	= 0x84001002,##		DCAMREC is invalid handle	##
        DCAMERR_FAILEDWRITEDATA		= 0x84001003,##		DCAMREC failed to write the data	##
        DCAMERR_FAILEDREADDATA		= 0x84001004,##		DCAMREC failed to read the data	##
        DCAMERR_NOWRECORDING		= 0x84001005,##		DCAMREC is recording data now	##
        DCAMERR_WRITEFULL			= 0x84001006,##		DCAMREC writes full frame of the session	##
        DCAMERR_ALREADYOCCUPIED		= 0x84001007,##		DCAMREC handle is already occupied by other HDCAM	##
        DCAMERR_TOOLARGEUSERDATASIZE= 0x84001008,##		DCAMREC is set the large value to user data size	##
        DCAMERR_NOIMAGE				= 0x84001804,##		not stored image in buffer on bufrecord ##
        DCAMERR_INVALIDWAITHANDLE	= 0x84002001,##		DCAMWAIT is invalid handle	##
        DCAMERR_NEWRUNTIMEREQUIRED	= 0x84002002,##		DCAM Module Version is older than the version that the camera requests	##
        DCAMERR_VERSIONMISMATCH		= 0x84002003,##		Camre returns the error on setting parameter to limit version	##
        DCAMERR_RUNAS_FACTORYMODE	= 0x84002004,##		Camera is running as a factory mode	##
        DCAMERR_IMAGE_UNKNOWNSIGNATURE	= 0x84003001,##	sigunature of image header is unknown or corrupted	##
        DCAMERR_IMAGE_NEWRUNTIMEREQUIRED= 0x84003002,## version of image header is newer than version that used DCAM supports	##
        DCAMERR_IMAGE_ERRORSTATUSEXIST	= 0x84003003,##	image header stands error status	##
        DCAMERR_IMAGE_HEADERCORRUPTED	= 0x84004004,##	image header value is strange	##
        DCAMERR_IMAGE_BROKENCONTENT		= 0x84004005,##	image content is corrupted	##

        ## calling error for DCAM-API 2.1.3 ##
        DCAMERR_UNKNOWNMSGID		= 0x80000801,##		unknown message id		##
        DCAMERR_UNKNOWNSTRID		= 0x80000802,##		unknown string id		##
        DCAMERR_UNKNOWNPARAMID		= 0x80000803,##		unkown parameter id		##
        DCAMERR_UNKNOWNBITSTYPE		= 0x80000804,##		unknown bitmap bits type			##
        DCAMERR_UNKNOWNDATATYPE		= 0x80000805,##		unknown frame data type				##

        ## internal error ##
        DCAMERR_NONE				= 0,		##		no error, nothing to have done		##
        DCAMERR_INSTALLATIONINPROGRESS=0x80000f00,##	installation progress				##
        DCAMERR_UNREACH				= 0x80000f01,##		internal error						##
        DCAMERR_UNLOADED			= 0x80000f04,##		calling after process terminated	##
        DCAMERR_THRUADAPTER			= 0x80000f05,##											##
        DCAMERR_NOCONNECTION		= 0x80000f07,##		HDCAM lost connection to camera		##

        DCAMERR_NOTIMPLEMENT		= 0x80000f02,##		not yet implementation				##

        DCAMERR_APIINIT_INITOPTIONBYTES	= 0xa4010003,##	DCAMAPI_INIT::initoptionbytes is invalid	##
        DCAMERR_APIINIT_INITOPTION		= 0xa4010004,##	DCAMAPI_INIT::initoption is invalid	##

        DCAMERR_INITOPTION_COLLISION_BASE=0xa401C000,
        DCAMERR_INITOPTION_COLLISION_MAX= 0xa401FFFF,

        ## Between DCAMERR_INITOPTION_COLLISION_BASE and DCAMERR_INITOPTION_COLLISION_MAX means there is collision with initoption in DCAMAPI_INIT. ##
        ## The value "(error code) - DCAMERR_INITOPTION_COLLISION_BASE" indicates the index which second INITOPTION group happens. ##

        ## success ##
        DCAMERR_SUCCESS				= 1			##		no error, general success code, app should check the value is positive	##


    ##
    # structures
    ##
    struct DCAM_GUID:
        pass

    struct DCAMAPI_INIT:
        pass

    struct DCAMDEV_OPEN:
        pass

    struct DCAMDEV_CAPABILITY:
        pass
    
    struct DCAMDEV_CAPABILITY_LUT:
        pass
    
    struct DCAMDEV_CAPABILITY_REGION:
        pass
    
    struct DCAMDEV_CAPABILITY_FRAMEOPTION:
        pass
    
    struct DCAMDEV_STRING:
        pass
    
    struct DCAMDATA_HDR:
        pass
    
    struct DCAMDATA_REGION:
        pass
    
    struct DCAMDATA_REGIONRECT:
        pass
    
    struct DCAMDATA_LUT:
        pass

    struct DCAMDATA_LINEARLUT:
        pass
    
    struct DCAMPROP_ATTR:
        pass

    struct DCAMPROP_VALUETEXT:
        pass 

    struct DCAMBUF_ATTACH:
        pass
    
    struct DCAM_TIMESTAMP:
        pass
    
    struct DCAMCAP_TRANSFERINFO:
        pass
    
    struct DCAMBUF_FRAME:
        pass
    
    struct DCAMWAIT_OPEN:
        pass

    struct DCAMWAIT_START:
        pass

    ##
    # functions
    ##
    # initialize, uninitialize and misc
    DCAMERR dcamapi_init			( DCAMAPI_INIT* param = 0 );
    DCAMERR dcamapi_uninit			();
    DCAMERR dcamdev_open			( DCAMDEV_OPEN* param );
    DCAMERR dcamdev_close			( HDCAM h );
    DCAMERR dcamdev_showpanel		( HDCAM h, int32 iKind );
    DCAMERR dcamdev_getcapability	( HDCAM h, DCAMDEV_CAPABILITY* param );
    DCAMERR dcamdev_getstring		( HDCAM h, DCAMDEV_STRING* param );
    DCAMERR dcamdev_setdata			( HDCAM h, DCAMDATA_HDR* param );
    DCAMERR dcamdev_getdata			( HDCAM h, DCAMDATA_HDR* param );

    # property control

    # buffer control

    # capturing

    # wait abort handle control
