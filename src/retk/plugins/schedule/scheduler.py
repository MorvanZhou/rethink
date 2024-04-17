import sched
import time

scheduler = sched.scheduler(time.time, time.sleep)
