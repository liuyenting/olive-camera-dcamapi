#cython: language_level=3

from cpython.exc cimport PyErr_SetFromErrnoWithFilenameObject
from libc.stdlib cimport malloc, free
from libc.string cimport memset

from recordclass import RecordClass

from dcamapi4 cimport *

cdef inline dcamdev_string( DCAMERR& err, HDCAM hdcam, int32 idStr, char* text, int32 textbytes ):
    cdef DCAMDEV_STRING param
    param.size = sizeof(param)
    param.text = text
    param.textbytes = textbytes
    param.iString = idStr

    # "Assignment to reference", https://github.com/cython/cython/issues/1863
    (&err)[0] = dcamdev_getstring( hdcam, &param )
    return not failed(err)


cdef show_dcamerr( HDCAM hdcam, DCAMERR errid, const char* apiname ):
    cdef DCAMERR err

    cdef char errtext[256]
    dcamdev_string( err, hdcam, errid, errtext, sizeof(errtext) )

    # retrieved error text
    msg = 'FAILED: (DCAMERR)0x{:08X} {} @ {}'.format(errid, errtext, apiname)
    PyErr_SetFromErrnoWithFilenameObject(RuntimeError, msg)


cdef show_dcamdev_info( HDCAM hdcam ):
    cdef char model[256]
    cdef char cameraid[64]
    cdef char bus[64]

    cdef DCAMERR err
    if not dcamdev_string( err, hdcam, DCAM_IDSTR_MODEL, model, sizeof(model) ):
        show_dcamerr( hdcam, err, 'dcamdev_getstring(DCAM_IDSTR_MODEL)')
    elif not dcamdev_string( err, hdcam, DCAM_IDSTR_CAMERAID, cameraid, sizeof(cameraid) ):
        show_dcamerr( hdcam, err, 'dcamdev_getstring(DCAM_IDSTR_CAMERAID)')
    elif not dcamdev_string( err, hdcam, DCAM_IDSTR_BUS, bus, sizeof(bus) ):
        show_dcamerr( hdcam, err, 'dcamdev_getstring(DCAM_IDSTR_BUS)')
    else:
        print('{} ({}) on {}'.format(model.decode('UTF-8'), cameraid.decode('UTF-8'), bus.decode('UTF-8')))


class SingletonInstance(RecordClass):
    instance: object
    refcnt: int


cdef class Singleton:
    _instances = {}

    @classmethod
    def init(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = SingletonInstance(cls(*args, **kwargs), 0)
        cls._instances[cls].refcnt += 1
        return cls._instances[cls].instance

    @classmethod
    def uninit(cls):
        cls._instances[cls].refcnt -= 1
        if cls._instances[cls].refcnt <= 0:
            del cls._instance[cls]


cdef class _DCAMAPI(Singleton):
    cdef dict devices 

    def __cinit__(self):
        cdef DCAMERR err

        cdef DCAMAPI_INIT apiinit
        memset(&apiinit, 0, sizeof(apiinit))
        apiinit.size = sizeof(apiinit)
        err = dcamapi_init(&apiinit)
        
        if failed(err):
            show_dcamerr( NULL, err, 'dcamapi_init()' )
        else:
            print('dcamapi_init() found {} devices'.format(apiinit.iDeviceCount))

            for iDevice in range(apiinit.iDeviceCount):
                show_dcamdev_info( <HDCAM>iDevice )
    
    def __dealloc__(self):
        print('dcamapi_uninit()')
        dcamapi_uninit()


cdef class DCAMAPI:
    #: device handle
    cdef HDCAM hdcam 
    
    def __init__(self, index=0):
        self.init()
        self.open(index)

    ##
    ## initialize, uninitialize and misc 
    ##
    def init(self):
        """
        Initialize the DCAM-API manager, modules and drivers.

        Only one session of DCAM-API can be open at any time, therefore, DCAMAPI wrapped _DCAMAPI to provide singleton behavior.
        """
        _DCAMAPI.init()
            
    def uninit(self):
        """
        Cleanups all resources and objects used by DCAM-API. 
        
        All opened devices will be forcefully closed. No new devices can be opened unless initialize again.
        """
        _DCAMAPI.uninit()

    def open(self, index):
        cdef DCAMERR err

        cdef DCAMDEV_OPEN devopen
        memset(&devopen, 0, sizeof(devopen))
        devopen.size = sizeof(devopen)
        devopen.index = index
        err = dcamdev_open(&devopen)

        if failed(err):
            show_dcamerr(NULL, err, 'dcamdev_open()')
        else:
            self.hdcam = <HDCAM>devopen.hdcam
    
    def close(self):
        cdef DCAMERR err

        err = dcamdev_close(self.hdcam)
        if failed(err):
            show_dcamerr(NULL, err, 'dcamdev_close()')
    ##
    ## initialize, uninitialize and misc 
    ##

    ##
    ## device data
    ##
    def get_capability(self, capability):  
        """Returns capability information not able to get from property."""
        """"
        if capability == LUT:
            pass
        elif capability == Region:
            pass
        elif capability == FrameOption:
            pass
        else:
            raise ValueError('unknown capability opton')
        """
        pass
        
    cpdef get_string(self, DCAM_IDSTR idstr, int32 nbytes=256):
        cdef char *text = <char *>malloc(nbytes * sizeof(char))

        cdef DCAMDEV_STRING param
        memset(&param, 0, sizeof(param))
        param.size = sizeof(param)
        param.text = text 
        param.textbytes = nbytes
        param.iString = idstr
        try:
            dcamdev_getstring(self.hdcam, &param)
            return text.decode('UTF-8')
        finally:
            free(text)

    def set_data(self):
        """
        Set the data that is impossible to set with property. WTF?
        """
        pass

    def get_data(self):
        """
        Get the data that is impossible to get from property. WTF!?
        """
        pass
    ##
    ## device data
    ##

    ##
    ## property control
    ##

    ##
    ## property control
    ##

    ##
    ## buffer control
    ##
    cpdef alloc(self, int32 nframes):
        """
        Allocates internal image buffers for image acquisition.
        """
        cdef DCAMERR err
        err = dcambuf_alloc(self.hdcam, nframes)
        if failed(err):
            show_dcamerr(self.hdcam, err, 'dcambuf_alloc()')
    
    def attach(self):
        pass
    
    def release(self):
        """
        Releases capturing buffer allocated by dcambuf_alloc() or assigned by dcambuf_attached().
        """
        cdef DCAMERR err
        err = dcambuf_release(self.hdcam)
        if failed(err):
            #TODO wait for busy state
            show_dcamerr(self.hdcam, err, 'dcambuf_release()')

    def lock_frame(self):
        pass 
    
    def copy_frame(self):
        pass 
    
    def copy_metadata(self):
        pass
    ##
    ## buffer control
    ##

    ##
    ## capturing
    ##
    def start(self, int32 mode):
        """
        Start capturing images.
        """
        cdef DCAMERR err
        err = dcamcap_start(self.hdcam, mode)
        if failed(err):
            show_dcamerr(self.hdcam, err, 'dcamcap_start()')

    def stop(self):
        """
        Terminates the acquisition.
        """
        cdef DCAMERR err
        err = dcamcap_stop(self.hdcam)
        if failed(err):
            show_dcamerr(self.hdcam, err, 'dcamcap_stop()')
    
    def status(self):
        """
        Returns current capturing status.
        """
        cdef DCAMERR err
        cdef int32 status
        err = dcamcap_status(self.hdcam, &status)
        if failed(err):
            show_dcamerr(self.hdcam, err, 'dcamcap_status()')
        else:
            #TODO convert capture status
            pass 
    
    def transfer_info(self):
        pass
    
    def fire_trigger(self):
        pass
    ##
    ## capturing
    ##

    ##
    ## wait abort handle control
    ##
    ##
    ## wait abort handle control
    ##