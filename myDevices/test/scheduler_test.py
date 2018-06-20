import pdb
import time
from myDevices.cloud.scheduler import SchedulerEngine, ScheduleItem
import myDevices.schedule as schedule
import datetime
from myDevices.utils.logger import exception, info, warn, error, debug, setDebug, setInfo
from myDevices.cloud.dbmanager import DbManager
import sqlite3
import threading
import json


class TestClient():
    def __init__(self):
        info('TestClient init')
        self.ran = False
    def RunAction(self, action):
        info('RunAction: ' + action)
        self.ran = True
    def SendNotification(self, notification):
        info('SendNotification: ' + notification)
   
   
class TestScheduler():
    def __init__(self):
        self.test_client = TestClient()
        self.test_engine = SchedulerEngine(self.test_client, 'test')
        self.added_ids = ()
        
    def add_scheduled_item(self, job):
        info('Add job: ' + str(job))
        retVal = self.test_engine.add_scheduled_item(job, True)
        if retVal == False:
            error('Add failed: ' + str(job))        
    
    def add_schedules(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'type':'date','title':'no_id_job','notify':'yes','actions':['action1'],'start_date':start_date})
        self.add_scheduled_item({'id':'1','type':'date','title':'date_job','notify':'yes','actions':['action1'],'start_date':start_date})
        self.add_scheduled_item({'id':'1','type':'date','title':'date_job_readd_same_id','notify':'yes','actions':['action1'],'start_date':start_date})
        self.add_scheduled_item({'id':'2','type':'interval','unit':'day','interval':1,'title':'daily_job','notify':'yes','actions':['action2'],'start_date':start_date})
        self.add_scheduled_item({'id':'3','type':'interval','unit':'day','interval':3,'title':'every_3_days_job','notify':'yes','actions':['action3'],'start_date':start_date})
        passed_date = datetime.datetime.strftime(datetime.datetime.utcnow() - datetime.timedelta(seconds=120), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'4','type':'date','title':'expired_date_job','notify':'yes','actions':['action1_expired'],'start_date':passed_date})
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'5','type':'date','title':'now_date_job','notify':'yes','actions':['action1_now'],'start_date':now})
        self.add_scheduled_item({'id':'6','type':'interval','unit':'week','interval':1,'title':'weekly_job','notify':'yes','actions':['action2'],'start_date':start_date})
        self.add_scheduled_item({'id':'7','type':'interval','unit':'week','interval':2,'title':'bi-weekly_job','notify':'yes','actions':['action2'],'start_date':start_date})
        one_day_ago = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60) - datetime.timedelta(days=1), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'8','type':'interval','unit':'day','interval':1,'title':'daily_job_started_one_day_ago','notify':'yes','actions':['action2'],'start_date':one_day_ago})
        one_day_from_now = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(days=1), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'9','type':'interval','unit':'day','interval':1,'title':'daily_job_starts_one_day_from_now','notify':'yes','actions':['action2'],'start_date':one_day_from_now})
        one_month_ago = datetime.datetime.strftime(schedule.month_delta(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), -1), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'10','type':'interval','unit':'month','interval':1,'title':'monthly_job_started_one_month_ago','notify':'yes','actions':['action3'],'start_date':one_month_ago})
        self.add_scheduled_item({'id':'11','type':'interval','unit':'month','interval':4,'title':'every_4_months_job','notify':'yes','actions':['action3'],'start_date':start_date})
        self.add_scheduled_item({'id':'12','type':'interval','unit':'month','interval':3,'title':'every_3_months_job','notify':'yes','actions':['action3'],'start_date':now})
        end_of_month = datetime.datetime.strftime(datetime.datetime(2015,1,31), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'13','type':'interval','unit':'month','interval':1,'title':'end_of_month_job','notify':'yes','actions':['action3'],'start_date':end_of_month})
        future_month = datetime.datetime.strftime(datetime.datetime(2017,12,31), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'14','type':'interval','unit':'month','interval':1,'title':'future_month_job','notify':'yes','actions':['action3'],'start_date':future_month})
        one_year_ago = datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
        one_year_ago = one_year_ago.replace(year=one_year_ago.year-1)
        one_year_ago = datetime.datetime.strftime(one_year_ago, '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'test','type':'interval','unit':'year','interval':1,'title':'yearly_job_started_one_year_ago','notify':'yes','actions':['action3'],'start_date':one_year_ago})
        self.add_scheduled_item({'id':'16','type':'interval','unit':'year','interval':2,'title':'every_2_years_job_started_one_year_ago','notify':'yes','actions':['action3'],'start_date':one_year_ago})
        future_year = datetime.datetime.strftime(datetime.datetime(2017,1,1), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'17','type':'interval','unit':'month','interval':1,'title':'future_year_job','notify':'yes','actions':['action3'],'start_date':future_year})
        one_week_ago = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60) - datetime.timedelta(days=7), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'18','type':'interval','unit':'week','interval':1,'title':'weekly_job_started_one_week_ago','notify':'yes','actions':['action2'],'start_date':one_week_ago})
        
    def update_schedules(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%d %H:%M')
        message = {}
        message['Schedules'] = []
        message['Schedules'].append({'Schedule':{'id':'1','type':'date','title':'updated_date_job','notify':'yes','actions':['action1_updated'],'start_date':start_date}})
        message['Schedules'].append({'Schedule':{'id':'18','type':'interval','unit':'day','interval':4,'title':'every_4_days_job','notify':'yes','actions':['action4'],'start_date':start_date}})
        self.test_engine.update_schedules(message)
    
    def remove_schedules(self, engine=None):
        if engine is None:
            engine = self.test_engine
        test_schedules = engine.get_schedules()
        for schedule_item in test_schedules:
            test_actions = ('action1', 'action2', 'action3', 'action4')
            if(schedule_item['actions'][0][:7] in test_actions):
                info('Remove job: ' + str(schedule_item['title']))
                retVal = engine.remove_scheduled_item(schedule_item)
                if retVal == False:
                    error('Removal failed: ' + str(schedule_item))

    def print_schedules(self):
        test_schedules = self.test_engine.get_schedules()
        info('TEST SCHEDULES: ' + str(test_schedules))

    def stop(self):
        self.test_engine.stop()
        
    def test_run_schedules(self):
        self.add_schedules()
        self.print_schedules()
        print('Pause to allow scheduled items to execute')
        time.sleep(60)
        print('Update schedules')
        self.update_schedules()
        self.print_schedules()
        print('Pause to allow scheduled items to execute')
        time.sleep(60)      
        
    def test_reload(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%d %H:%M')
        self.add_scheduled_item({'id':'1','type':'date','title':'date_job','notify':'yes','actions':['action1'],'start_date':start_date})
        self.add_scheduled_item({'id':'2','type':'interval','unit':'day','interval':1,'title':'daily_job','notify':'yes','actions':['action2'],'start_date':start_date})
        print('Pause to allow scheduled items to execute')
        done_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
        while not self.test_client.ran and datetime.datetime.utcnow() < done_time:
            time.sleep(1)
        self.stop()
        reload_test_client = TestClient()
        reload_test_engine = SchedulerEngine(reload_test_client, 'test')
        print('Pause to give reloaded scheduled items time to execute even though they should not actually run')
        done_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
        while not reload_test_client.ran and datetime.datetime.utcnow() < done_time:
            time.sleep(1)
        self.remove_schedules(reload_test_engine)
        reload_test_engine.stop()

    def test_delayed_load(self):
        self.stop()
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%d %H:%M')
        scheduled_items = []
        scheduled_items.append({'id':'reload_test1','type':'date','title':'date_job','notify':'yes','actions':['action1'],'start_date':now})
        scheduled_items.append({'id':'reload_test2','type':'interval','unit':'day','interval':1,'title':'daily_job','notify':'yes','actions':['action2'],'start_date':now})
        scheduled_items.append({'id':'reload_test3','type':'interval','unit':'week','interval':1,'title':'weekly_job','notify':'yes','actions':['action2'],'start_date':now})
        scheduled_items.append({'id':'reload_test4','type':'interval','unit':'month','interval':1,'title':'monthly_job','notify':'yes','actions':['action2'],'start_date':now})
        scheduled_items.append({'id':'reload_test5','type':'interval','unit':'year','interval':1,'title':'yearly_job','notify':'yes','actions':['action2'],'start_date':now})
        for item in scheduled_items:
            item_json = json.dumps(item)
            try:
                DbManager.Insert('scheduled_settings', item['id'], item_json)
            except sqlite3.IntegrityError as e:
                setClause =  'data = ?'
                whereClause = 'id = ?'
                DbManager.Update('scheduled_settings', setClause, item_json, whereClause, item['id'])
        print('Pause before loading scheduler')
        time.sleep(20)
        print('Starting scheduler, time is {}'.format(datetime.datetime.utcnow()))
        delayed_test_client = TestClient()
        delayed_test_engine = SchedulerEngine(delayed_test_client, 'test')
        done_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
        while not delayed_test_client.ran and datetime.datetime.utcnow() < done_time:
            time.sleep(1)
        time.sleep(5)    
        self.remove_schedules(delayed_test_engine)
        delayed_test_engine.stop()
        
    def test_concurrent_updates(self):
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%d %H:%M')
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'1','type':'date','title':'date_job1','notify':'yes','actions':['action1'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'1','type':'date','title':'date_job1_updated','notify':'yes','actions':['action1'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'2','type':'interval','unit':'day','interval':1,'title':'daily_job2','notify':'yes','actions':['action2'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'2','type':'interval','unit':'day','interval':1,'title':'daily_job2_updated','notify':'yes','actions':['action2'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'3','type':'interval','unit':'week','interval':1,'title':'weekly_job3','notify':'yes','actions':['action2'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'3','type':'interval','unit':'week','interval':1,'title':'weekly_job3_updated','notify':'yes','actions':['action2'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'4','type':'interval','unit':'month','interval':1,'title':'monthly_job4','notify':'yes','actions':['action2'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'4','type':'interval','unit':'month','interval':1,'title':'monthly_job4_updated','notify':'yes','actions':['action2'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'5','type':'interval','unit':'year','interval':1,'title':'yearly_job5','notify':'yes','actions':['action2'],'start_date':now},)).start()
        threading.Thread(target=self.update_schedule, daemon=True, args=({'id':'5','type':'interval','unit':'year','interval':1,'title':'yearly_job5_updated','notify':'yes','actions':['action2'],'start_date':now},)).start()
        #Short pause here, 0.5 seconds or so, should cause only update_all_schedules items to run. Longer pause should cause above items to run (one per id), followed by the update_all_schedules items.
        time.sleep(1)
        threading.Thread(target=self.update_all_schedules, daemon=True).start()
        time.sleep(5)
    
    def update_schedule(self, new_item):
        self.add_scheduled_item(new_item)
    
    def update_all_schedules(self):
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%d %H:%M')
        message = {}
        message['Schedules'] = []
        message['Schedules'].append({'Schedule':{'id':'3','type':'interval','unit':'week','interval':1,'title':'weekly_job3_full_update','notify':'yes','actions':['action2'],'start_date':now}})
        message['Schedules'].append({'Schedule':{'id':'4','type':'interval','unit':'month','interval':1,'title':'monthly_job4_full_update','notify':'yes','actions':['action2'],'start_date':now}})
        message['Schedules'].append({'Schedule':{'id':'5','type':'interval','unit':'year','interval':1,'title':'yearly_job5_full_update','notify':'yes','actions':['action2'],'start_date':now}})
        message['Schedules'].append({'Schedule':{'id':'6','type':'date','title':'date_job6_full_update','notify':'yes','actions':['action1'],'start_date':now}})
        message['Schedules'].append({'Schedule':{'id':'7','type':'interval','unit':'day','interval':1,'title':'daily_job7_full_update','notify':'yes','actions':['action2'],'start_date':now}})
        message['Schedules'].append({'Schedule':{'id':'7','type':'interval','unit':'day','interval':1,'title':'daily_job7_full_update2','notify':'yes','actions':['action2'],'start_date':now}})
        message['Schedules'].append({'Schedule':{'id':'8','type':'interval','unit':'week','interval':1,'title':'weekly_job8_full_update','notify':'yes','actions':['action2'],'start_date':now}})
        self.test_engine.update_schedules(message)
        
if __name__ == '__main__':
    #setDebug()
    setInfo()
    test_scheduler = TestScheduler()
    # test_scheduler.test_run_schedules()
    test_scheduler.test_concurrent_updates()
    # test_scheduler.test_delayed_load()
    test_scheduler.test_reload()   
    test_scheduler.remove_schedules()
    test_scheduler.print_schedules()
    test_scheduler.stop()