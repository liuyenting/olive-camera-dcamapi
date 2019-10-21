from pprint import pprint

import coloredlogs

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)


driver = DCAMAPI()

driver.initialize()

pprint(driver.enumerate_devices())
pprint()

driver.shutdown()
