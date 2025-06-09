from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from .jobs import schedule_api
from datetime import datetime, timedelta

def start():
	
	scheduler = BackgroundScheduler()
	scheduler.remove_all_jobs()
	scheduler.start()
	scheduler.add_job(schedule_api, 'interval', seconds=300,coalesce=True,
        max_instances=1)
	# 