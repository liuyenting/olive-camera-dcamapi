from olive.drivers.dcamapi.wrapper import DCAMAPI

api = DCAMAPI()
print("pre-init")
api.init()
print("post-init")

print("pre-uninit")
api.uninit()
print("post-uninit")

