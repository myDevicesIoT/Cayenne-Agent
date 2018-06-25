import datetime
import json
import pdb
import sqlite3
import threading
import time
import unittest

import myDevices.schedule as schedule
from myDevices.cloud.dbmanager import DbManager
from myDevices.cloud.scheduler import SchedulerEngine
from myDevices.utils.logger import debug, error, exception, info, setDebug, setInfo, warn


class TestClient():
    def __init__(self):
        info('TestClient init')
        self.actions_ran = []

    def RunAction(self, action):
        info('RunAction: ' + action)
        self.actions_ran.append(action)

    def SendNotification(self, notification):
        info('SendNotification: ' + notification)


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        self.test_client = TestClient()
        self.test_engine = SchedulerEngine(self.test_client, 'test')
        self.schedule_events = []

    def tearDown(self):
        self.remove_schedules()
        self.test_engine.stop()

    def add_schedules(self, schedule_events):
        for event in schedule_events:
            self.test_engine.add_scheduled_event(event, True)
        self.schedule_events = self.schedule_events + schedule_events

    def remove_schedules(self, engine=None):
        scheduled_events = {event['id']:event for event in self.schedule_events if 'id' in event}
        for event in scheduled_events.values():
            self.assertTrue(self.test_engine.remove_scheduled_event(event))

    def check_schedules_added(self, expected):
        actual = self.test_engine.get_scheduled_events()
        self.assertCountEqual(expected, actual)

    def check_schedules_run(self, expected, skip_jobs=()):
        print('Pause to allow scheduled events to execute')
        expected_to_run = [action for event in expected if event['title'] not in skip_jobs for action in event['actions']]
        for i in range(70):
            time.sleep(1)
            if len(expected_to_run) > 0 and len(expected_to_run) == len(self.test_client.actions_ran):
                break
        self.assertCountEqual(expected_to_run, self.test_client.actions_ran)

    def test_missing_id(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%d %H:%M')
        missing_id_event = {'type':'date', 'title':'no_id_job', 'notify':'yes', 'actions':['no_id_job_action'], 'start_date':start_date}
        self.assertFalse(self.test_engine.add_scheduled_event(missing_id_event, True))
        self.assertFalse(self.test_engine.get_scheduled_events())

    def test_overwrite_job(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%d %H:%M')
        schedule_events = [{'id':'overwrite_1', 'type':'date', 'title':'overwritten_job', 'notify':'yes', 'actions':['overwritten_job_action'], 'start_date':start_date},
            {'id':'overwrite_1', 'type':'date', 'title':'date_job_readd_same_id', 'notify':'yes', 'actions':['date_job_readd_same_id_action'], 'start_date':start_date}]
        self.add_schedules(schedule_events)
        expected = [event for event in schedule_events if 'id' in event and event['title'] != 'overwritten_job']
        self.check_schedules_added(expected)

    def test_current_schedules(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%d %H:%M')
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%d %H:%M')
        schedule_events = [{'id':'current_1', 'type':'date', 'title':'date_job', 'notify':'yes', 'actions':['date_job_action'], 'start_date':start_date},
            {'id':'current_2', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job', 'notify':'yes', 'actions':['daily_job_action'], 'start_date':start_date},
            {'id':'current_3', 'type':'interval', 'unit':'day', 'interval':3, 'title':'every_3_days_job', 'notify':'yes', 'actions':['every_3_days_job_action'], 'start_date':start_date},
            {'id':'current_4', 'type':'date', 'title':'now_date_job', 'notify':'yes', 'actions':['now_date_job_action'], 'start_date':now},
            {'id':'current_5', 'type':'interval', 'unit':'week', 'interval':1, 'title':'weekly_job', 'notify':'yes', 'actions':['weekly_job_action'], 'start_date':start_date},
            {'id':'current_6', 'type':'interval', 'unit':'week', 'interval':2, 'title':'bi-weekly_job', 'notify':'yes', 'actions':['weekly_job_action'], 'start_date':start_date},
            {'id':'current_7', 'type':'interval', 'unit':'month', 'interval':4, 'title':'every_4_months_job', 'notify':'yes', 'actions':['every_4_months_job_action'], 'start_date':start_date},
            {'id':'current_8', 'type':'interval', 'unit':'month', 'interval':3, 'title':'every_3_months_job', 'notify':'yes', 'actions':['every_3_months_job_action'], 'start_date':now}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        self.check_schedules_run(schedule_events)

    def test_past_schedules(self):
        next_minute = datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
        passed_date = datetime.datetime.strftime(datetime.datetime.utcnow() - datetime.timedelta(seconds=120), '%Y-%m-%d %H:%M')
        one_day_ago = datetime.datetime.strftime(next_minute - datetime.timedelta(days=1), '%Y-%m-%d %H:%M')
        one_week_ago = datetime.datetime.strftime(next_minute - datetime.timedelta(days=7), '%Y-%m-%d %H:%M')
        one_month_ago = datetime.datetime.strftime(schedule.month_delta(next_minute, -1), '%Y-%m-%d %H:%M')
        one_year_ago = next_minute.replace(year=next_minute.year-1)
        one_year_ago = datetime.datetime.strftime(one_year_ago, '%Y-%m-%d %H:%M')
        schedule_events = [{'id':'past_1', 'type':'date', 'title':'expired_date_job', 'notify':'yes', 'actions':['expired_date_job_action'], 'start_date':passed_date},
            {'id':'past_2', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job_started_one_day_ago', 'notify':'yes', 'actions':['daily_job_started_one_day_ago_action'], 'start_date':one_day_ago},
            {'id':'past_3', 'type':'interval', 'unit':'month', 'interval':1, 'title':'monthly_job_started_one_month_ago', 'notify':'yes', 'actions':['monthly_job_started_one_month_ago_action'], 'start_date':one_month_ago},
            {'id':'past_4', 'type':'interval', 'unit':'year', 'interval':1, 'title':'yearly_job_started_one_year_ago', 'notify':'yes', 'actions':['yearly_job_started_one_year_ago_action'], 'start_date':one_year_ago},
            {'id':'past_5', 'type':'interval', 'unit':'year', 'interval':2, 'title':'every_2_years_job_started_one_year_ago', 'notify':'yes', 'actions':['every_2_years_job_started_one_year_ago_action'], 'start_date':one_year_ago},
            {'id':'past_6', 'type':'interval', 'unit':'week', 'interval':1, 'title':'weekly_job_started_one_week_ago', 'notify':'yes', 'actions':['weekly_job_started_one_week_ago_action'], 'start_date':one_week_ago}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        self.check_schedules_run(schedule_events, ('expired_date_job', 'every_2_years_job_started_one_year_ago'))

    def test_future_schedules(self):
        one_day_from_now = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(days=1), '%Y-%m-%d %H:%M')
        end_of_month = datetime.datetime.strftime(datetime.datetime(2015,1,31), '%Y-%m-%d %H:%M')
        future_month = datetime.datetime.strftime(datetime.datetime(2017,12,31), '%Y-%m-%d %H:%M')
        future_year = datetime.datetime.strftime(datetime.datetime(2017,1,1), '%Y-%m-%d %H:%M')
        schedule_events = [{'id':'future_1', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job_starts_one_day_from_now', 'notify':'yes', 'actions':['daily_job_starts_one_day_from_now_action'], 'start_date':one_day_from_now},
            {'id':'future_2', 'type':'interval', 'unit':'month', 'interval':1, 'title':'end_of_month_job', 'notify':'yes', 'actions':['end_of_month_job_action'], 'start_date':end_of_month},
            {'id':'future_3', 'type':'interval', 'unit':'month', 'interval':1, 'title':'future_month_job', 'notify':'yes', 'actions':['future_month_job_action'], 'start_date':future_month},
            {'id':'future_4', 'type':'interval', 'unit':'month', 'interval':1, 'title':'future_year_job', 'notify':'yes', 'actions':['future_year_job_action'], 'start_date':future_year}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        skip_jobs = [event['title'] for event in schedule_events]
        self.check_schedules_run(schedule_events, skip_jobs)

    def test_reload(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%d %H:%M')
        schedule_events = [{'id':'reload_1', 'type':'date', 'title':'date_job', 'notify':'yes', 'actions':['date_job_action'], 'start_date':start_date},
            {'id':'reload_2', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job', 'notify':'yes', 'actions':['daily_job_action'], 'start_date':start_date}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        self.check_schedules_run(schedule_events)
        self.test_engine.stop()
        del self.test_engine
        del self.test_client
        self.test_client = TestClient()
        self.test_engine = SchedulerEngine(self.test_client, 'test')
        self.check_schedules_added(schedule_events)
        self.check_schedules_run(schedule_events, ('date_job', 'daily_job'))

    def test_delayed_load(self):
        self.test_engine.stop()
        del self.test_engine
        del self.test_client
        now = datetime.datetime.utcnow()
        if (now.second > 35):
            print('Sleep until the minute rolls over')
            time.sleep(60 - now.second)
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%d %H:%M')
        self.schedule_events = [{'id':'delay_1', 'type':'date', 'title':'date_job', 'notify':'yes', 'actions':['date_job_action'], 'start_date':now},
            {'id':'delay_2', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job', 'notify':'yes', 'actions':['daily_job_action'], 'start_date':now},
            {'id':'delay_3', 'type':'interval', 'unit':'week', 'interval':1, 'title':'weekly_job', 'notify':'yes', 'actions':['weekly_job_action'], 'start_date':now},
            {'id':'delay_4', 'type':'interval', 'unit':'month', 'interval':1, 'title':'monthly_job', 'notify':'yes', 'actions':['monthly_job_action'], 'start_date':now},
            {'id':'delay_5', 'type':'interval', 'unit':'year', 'interval':1, 'title':'yearly_job', 'notify':'yes', 'actions':['yearly_job_action'], 'start_date':now}]
        for event in self.schedule_events:
            event_json = json.dumps(event)
            try:
                DbManager.Insert('scheduled_events', event['id'], event_json)
            except sqlite3.IntegrityError as e:
                DbManager.Update('scheduled_events', 'event = ?', event_json, 'id = ?', event['id'])
        print('Pause before loading scheduler')
        time.sleep(20)
        print('Starting scheduler, time is {}'.format(datetime.datetime.utcnow()))
        self.test_client = TestClient()
        self.test_engine = SchedulerEngine(self.test_client, 'test')
        self.check_schedules_run(self.schedule_events)

    def test_concurrent_updates(self):
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%d %H:%M')
        schedule_events = [{'id':'concurrent_1', 'type':'date', 'title':'date_job', 'notify':'yes', 'actions':['date_job_action'], 'start_date':now},
            {'id':'concurrent_1', 'type':'date', 'title':'date_job_updated', 'notify':'yes', 'actions':['date_job_action'], 'start_date':now},
            {'id':'concurrent_2', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job', 'notify':'yes', 'actions':['daily_job_action'], 'start_date':now},
            {'id':'concurrent_2', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job_updated', 'notify':'yes', 'actions':['daily_job_action'], 'start_date':now},
            {'id':'concurrent_3', 'type':'interval', 'unit':'week', 'interval':1, 'title':'weekly_job', 'notify':'yes', 'actions':['weekly_job_action'], 'start_date':now},
            {'id':'concurrent_3', 'type':'interval', 'unit':'week', 'interval':1, 'title':'weekly_job_updated', 'notify':'yes', 'actions':['weekly_job_action'], 'start_date':now},
            {'id':'concurrent_4', 'type':'interval', 'unit':'month', 'interval':1, 'title':'monthly_job', 'notify':'yes', 'actions':['monthly_job_action'], 'start_date':now},
            {'id':'concurrent_4', 'type':'interval', 'unit':'month', 'interval':1, 'title':'monthly_job_updated', 'notify':'yes', 'actions':['monthly_job_action'], 'start_date':now},
            {'id':'concurrent_5', 'type':'interval', 'unit':'year', 'interval':1, 'title':'yearly_job', 'notify':'yes', 'actions':['yearly_job_action'], 'start_date':now},
            {'id':'concurrent_5', 'type':'interval', 'unit':'year', 'interval':1, 'title':'yearly_job_updated', 'notify':'yes', 'actions':['yearly_job_action'], 'start_date':now}]
        for event in schedule_events:
            threading.Thread(target=self.add_schedules, daemon=True, args=([event],)).start()
        #Only half the schedule_events should run since ones with the same id will overwrite previously added ones. Since we don't know what order that will take
        #we just make sure we only check that one of each action has run.
        run_events = {event['id']:event for event in schedule_events if 'id' in event}
        skip_jobs = [event['title'] for event in run_events.values()]
        self.check_schedules_run(schedule_events, skip_jobs)
    
    def test_update_schedules(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%d %H:%M')
        schedule_events = [{'id':'update_1', 'type':'date', 'title':'date_job', 'notify':'yes', 'actions':['date_job_action'], 'start_date':start_date},
            {'id':'update_2', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job', 'notify':'yes', 'actions':['daily_job_action'], 'start_date':start_date}]
        self.add_schedules(schedule_events)
        update_schedule_events = [{'id':'update_3', 'type':'date', 'title':'date_job_full_update', 'notify':'yes', 'actions':['date_job_full_update_action'], 'start_date':start_date},
            {'id':'update_4', 'type':'interval', 'unit':'day', 'interval':1, 'title':'daily_job_full_update', 'notify':'yes', 'actions':['daily_job_full_update_action'], 'start_date':start_date}]
        self.assertTrue(self.test_engine.update_scheduled_events(update_schedule_events))
        self.schedule_events = update_schedule_events
        self.check_schedules_run(update_schedule_events)
        

if __name__ == '__main__':
    # setDebug()
    setInfo()
    unittest.main()
    # test_suite = unittest.TestSuite()
    # test_suite.addTest(SchedulerTest('test_current_schedules'))
    # # test_suite.addTest(SchedulerTest('test_future_schedules'))
    # # test_suite.addTest(SchedulerTest('test_reload'))
    # # test_suite.addTest(SchedulerTest('test_delayed_load'))
    # unittest.TextTestRunner().run(test_suite)

