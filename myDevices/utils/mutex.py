from threading import local
from contextlib import contextmanager
from myDevices.utils.logger import exception, info, warn, error, debug
local = local()
@contextmanager
def acquire(*locks):
    locks = sorted(locks, key=lambda x: id(x))   
    acquired = getattr(local,"acquired",[])
    # Check to make sure we're not violating the order of locks already acquired   
    if acquired:
        if max(id(lock) for lock in acquired) >= id(locks[0]):
            #raise RuntimeError("Lock Order Violation")
            exception("Lock Order Violation")
    acquired.extend(locks)
    local.acquired = acquired
    try:
        for lock in locks:
            lock.acquire()
        yield
    finally:
        for lock in reversed(locks):
            lock.release()
        del acquired[-len(locks):]