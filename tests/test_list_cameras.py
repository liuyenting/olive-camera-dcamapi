from olive.drivers.dcamapi import DCAMAPI

driver = DCAMAPI()

driver.initialize()

from pprint import pprint

pprint(driver.enumerate_devices())

driver.shutdown()
