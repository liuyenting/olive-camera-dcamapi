#cython: language_level=3

from cpython cimport bool as pybool
from cpython.exc cimport PyErr_SetFromErrnoWithFilenameObject
cimport cython
from libc.stdlib cimport malloc, free
from libc.string cimport memset

from enum import auto, Enum, IntEnum

from dcamapi cimport *

class Info(IntEnum):
    Bus             = DCAM_IDSTR.DCAM_IDSTR_BUS
    CameraID        = DCAM_IDSTR.DCAM_IDSTR_CAMERAID
    Vendor          = DCAM_IDSTR.DCAM_IDSTR_VENDOR
    Model           = DCAM_IDSTR.DCAM_IDSTR_MODEL
    CameraVersion   = DCAM_IDSTR.DCAM_IDSTR_CAMERAVERSION
    DriverVersion   = DCAM_IDSTR.DCAM_IDSTR_DRIVERVERSION
    ModuleVersion   = DCAM_IDSTR.DCAM_IDSTR_MODULEVERSION
    APIVersion      = DCAM_IDSTR.DCAM_IDSTR_DCAMAPIVERSION

class Capability(Enum):
    LUT = auto()
    Region = auto()
    FrameOption = auto()


@cython.final
cdef class DCAMAPI:
    """
    Wrapper class for the API.

    DCAM-API can ONLY INSTANTIATE ONCE.
    """
    #: number of supported devices found by DCAM-API
    cdef readonly int32 n_devices

    def init(self):
        """
        Initialize the DCAM-API manager, modules and drivers.

        Only one session of DCAM-API can be open at any time, therefore, DCAMAPI wrapped _DCAMAPI, who provides the singleton behavior.
        """
        cdef DCAMERR err

        cdef DCAMAPI_INIT apiinit
        memset(&apiinit, 0, sizeof(apiinit))
        apiinit.size = sizeof(apiinit)
        err = dcamapi_init(&apiinit)
        DCAMAPI.check_error(err, 'dcamapi_init()')

        self.n_devices = apiinit.iDeviceCount

    def  uninit(self):
        """
        Cleanups all resources and objects used by DCAM-API.

        All opened devices will be forcefully closed. No new devices can be opened unless initialize again.
        """
        dcamapi_uninit()

    ##

    cpdef open(self, int32 index):
        cdef DCAMERR err

        cdef DCAMDEV_OPEN devopen
        memset(&devopen, 0, sizeof(devopen))
        devopen.size = sizeof(devopen)
        devopen.index = index
        err = dcamdev_open(&devopen)
        DCAMAPI.check_error(err, 'dcamdev_open()')

        return <object>devopen.hdcam

    cpdef close(self, DCAM dev):
        cdef DCAMERR err

        err = dcamdev_close(dev.handle)
        DCAMAPI.check_error(err, 'dcamdev_close()')

    ##

    @staticmethod
    cdef check_error(DCAMERR errid, const char* apiname, HDCAM hdcam=NULL):
        if not failed(errid):
            return

        # implicit string reader for fast access
        cdef char errtext[256]

        cdef DCAMDEV_STRING param
        memset(&param, 0, sizeof(param))
        param.size = sizeof(param)
        param.text = errtext
        param.textbytes = sizeof(errtext)
        param.iString = errid
        dcamdev_getstring(hdcam, &param)

        # restrict errid to 32-bits to match C-style output
        raise RuntimeError(
            '{}, (DCAMERR)0x{:08X} {}'.format(apiname.decode('UTF-8'), errid&0xFFFFFFFF, errtext.decode('UTF-8'))
        )

@cython.final
cdef class DCAM:
    """Base class for the device."""
    cdef HDCAM handle

    def __cinit__(self, handle):
        self.handle = <HDCAM>handle

    ##
    ## device data
    ##
    def get_capability(self, capability: Capability):
        """Returns capability information not able to get from property."""
        try:
            return {
                Capability.Region: self._get_capability_region,
                Capability.LUT: self._get_capability_lut,
                Capability.FrameOption: self._get_capability_frameoption
            }[capability]()
        except KeyError:
            raise ValueError('unknown capability option')

    def _get_capability_region(self):
        cdef DCAMERR err

        cdef DCAMDEV_CAPABILITY_REGION param
        memset(&param, 0, sizeof(param))
        param.hdr.size = sizeof(param)
        param.hdr.domain = DCAMDEV_CAPDOMAIN.DCAMDEV_CAPDOMAIN__DCAMDATA
        param.hdr.kind = DCAMDATA_KIND.DCAMDATA_KIND__REGION

        err = dcamdev_getcapability(self.handle, &param.hdr)
        DCAMAPI.check_error(err, 'dcamdev_getcapbility()', self.handle)

        attributes = dict()
        attributes['units'] = {'horizontal': param.horzunit, 'vertical': param.vertunit}

        region_type = param.hdr.capflag & DCAMDATA_REGIONTYPE.DCAMDATA_REGIONTYPE__BODYMASK
        attributes['type'] = []
        if region_type == DCAMDATA_REGIONTYPE.DCAMDATA_REGIONTYPE__NONE:
            pass
        else:
            if region_type == DCAMDATA_REGIONTYPE.DCAMDATA_REGIONTYPE__RECT16ARRAY:
                attributes['type'].append('rect16array')
            if region_type == DCAMDATA_REGIONTYPE.DCAMDATA_REGIONTYPE__BYTEMASK:
                attributes['type'].append('bytemask')

        return attributes


    def _get_capability_lut(self):
        cdef DCAMERR err

        cdef DCAMDEV_CAPABILITY_LUT param
        memset(&param, 0, sizeof(param))
        param.hdr.size = sizeof(param)
        param.hdr.domain = DCAMDEV_CAPDOMAIN.DCAMDEV_CAPDOMAIN__DCAMDATA
        param.hdr.kind = DCAMDATA_KIND.DCAMDATA_KIND__LUT

        raise NotImplementedError

    def _get_capability_frameoption(self):
        cdef DCAMERR err

        cdef DCAMDEV_CAPABILITY_FRAMEOPTION param
        memset(&param, 0, sizeof(param))
        param.hdr.size = sizeof(param)
        param.hdr.domain = DCAMDEV_CAPDOMAIN.DCAMDEV_CAPDOMAIN__FRAMEOPTION

        err = dcamdev_getcapability(self.handle, &param.hdr)
        DCAMAPI.check_error(err, 'dcamdev_getcapbility()', self.handle)

        if param.hdr.capflag == 0:
            raise RuntimeError('frame option is currently disabled')

        flags = {
            'highcontrast': DCAMBUF_PROCTYPE.DCAMBUF_PROCTYPE__HIGHCONTRASTMODE
        }
        return {
            key: <pybool>(param.hdr.capflag & value)
            for key, value in flags.items()
        }

    cpdef get_string(self, int32 idstr, int32 nbytes=256):
        cdef char *text = <char *>malloc(nbytes * sizeof(char))

        cdef DCAMDEV_STRING param
        memset(&param, 0, sizeof(param))
        param.size = sizeof(param)
        param.text = text
        param.textbytes = nbytes
        param.iString = idstr
        try:
            dcamdev_getstring(self.handle, &param)
            return text.decode('utf--8', errors='replace')
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
        err = dcambuf_alloc(self.handle, nframes)
        DCAMAPI.check_error(err, 'dcambuf_alloc()', self.handle)

    def attach(self):
        pass

    def release(self):
        """
        Releases capturing buffer allocated by dcambuf_alloc() or assigned by dcambuf_attached().
        """
        cdef DCAMERR err
        err = dcambuf_release(self.handle)
        DCAMAPI.check_error(err, 'dcambuf_release()', self.handle)
        #TODO wait for busy state

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
        err = dcamcap_start(self.handle, mode)
        DCAMAPI.check_error(err, 'dcamcap_start()', self.handle)

    def stop(self):
        """
        Terminates the acquisition.
        """
        cdef DCAMERR err
        err = dcamcap_stop(self.handle)
        DCAMAPI.check_error(err, 'dcamcap_stop()', self.handle)

    def status(self):
        """
        Returns current capturing status.
        """
        cdef DCAMERR err
        cdef int32 status
        err = dcamcap_status(self.handle, &status)
        DCAMAPI.check_error(err, 'dcamcap_status()', self.handle)
        #TODO convert capture status

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