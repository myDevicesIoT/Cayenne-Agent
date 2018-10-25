import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
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
        return True

    def SendNotification(self, notification):
        info('SendNotification: ' + notification)


class TestHandler(BaseHTTPRequestHandler):
    def handle_payload(self):
        data = self.rfile.read(int(self.headers.get('Content-Length'))).decode('utf-8')
        self.server.received.append(json.loads(data))
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # This should match the payload in test_http_notification
        self.server.received.append({'test':'GET request'})

    def do_POST(self):
        self.handle_payload()

    def do_PUT(self):
        self.handle_payload()

    def do_DELETE(self):
        # This should match the payload in test_http_notification
        self.server.received.append({'test':'DELETE request'})


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
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
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%dT%H:%M:%S.%fZ')
        missing_id_event = {'title':'no_id_job', 'actions':['no_id_job_action'], 'config':{'type':'date', 'start_date':start_date}}
        self.assertFalse(self.test_engine.add_scheduled_event(missing_id_event, True))
        self.assertFalse(self.test_engine.get_scheduled_events())

    def test_overwrite_job(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%dT%H:%M:%S.%fZ')
        schedule_events = [{'id':'overwrite_1', 'title':'overwritten_job', 'actions':['overwritten_job_action'], 'config':{'type':'date', 'start_date':start_date}},
            {'id':'overwrite_1', 'title':'date_job_readd_same_id', 'actions':['date_job_readd_same_id_action'], 'config':{'type':'date', 'start_date':start_date}}]
        self.add_schedules(schedule_events)
        expected = [event for event in schedule_events if 'id' in event and event['title'] != 'overwritten_job']
        self.check_schedules_added(expected)

    def test_current_schedules(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%dT%H:%M:%S.%fZ')
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%dT%H:%M:%S.%fZ')
        schedule_events = [{'id':'current_1', 'title':'date_job', 'actions':['date_job_action'], 'config':{'type':'date', 'start_date':start_date}},
            {'id':'current_2', 'title':'daily_job', 'actions':['daily_job_action'], 'config': {'type':'interval', 'unit':'day', 'interval':1, 'start_date':start_date}},
            {'id':'current_3', 'title':'every_3_days_job', 'actions':['every_3_days_job_action'], 'config':{'type':'interval', 'unit':'day', 'interval':3, 'start_date':start_date}},
            {'id':'current_4', 'title':'now_date_job', 'actions':['now_date_job_action'], 'config':{'type':'date', 'start_date':now}},
            {'id':'current_5', 'title':'weekly_job', 'actions':['weekly_job_action'], 'config':{'type':'interval', 'unit':'week', 'interval':1, 'start_date':start_date}},
            {'id':'current_6', 'title':'bi-weekly_job', 'actions':['weekly_job_action'], 'config':{'type':'interval', 'unit':'week', 'interval':2, 'start_date':start_date}},
            {'id':'current_7', 'title':'every_4_months_job', 'actions':['every_4_months_job_action'], 'config':{'type':'interval', 'unit':'month', 'interval':4, 'start_date':start_date}},
            {'id':'current_8', 'title':'every_3_months_job', 'actions':['every_3_months_job_action'], 'config':{'type':'interval', 'unit':'month', 'interval':3, 'start_date':now}},
            {'id':'current_9', 'title':'hourly_job', 'actions':['hourly_job_action'], 'config': {'type':'interval', 'unit':'hour', 'interval':1, 'start_date':start_date}}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        self.check_schedules_run(schedule_events)

    def test_past_schedules(self):
        next_minute = datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
        passed_date = datetime.datetime.strftime(datetime.datetime.utcnow() - datetime.timedelta(seconds=120), '%Y-%m-%dT%H:%M:%S.%fZ')
        one_day_ago = datetime.datetime.strftime(next_minute - datetime.timedelta(days=1), '%Y-%m-%dT%H:%M:%S.%fZ')
        one_week_ago = datetime.datetime.strftime(next_minute - datetime.timedelta(days=7), '%Y-%m-%dT%H:%M:%S.%fZ')
        one_month_ago = datetime.datetime.strftime(schedule.month_delta(next_minute, -1), '%Y-%m-%dT%H:%M:%S.%fZ')
        one_year_ago = next_minute.replace(year=next_minute.year-1)
        one_year_ago = datetime.datetime.strftime(one_year_ago, '%Y-%m-%dT%H:%M:%S.%fZ')
        schedule_events = [{'id':'past_1', 'title':'expired_date_job', 'actions':['expired_date_job_action'], 'config':{'type':'date', 'start_date':passed_date}},
            {'id':'past_2', 'title':'daily_job_started_one_day_ago', 'actions':['daily_job_started_one_day_ago_action'], 'config':{'type':'interval', 'unit':'day', 'interval':1, 'start_date':one_day_ago}},
            {'id':'past_3', 'title':'monthly_job_started_one_month_ago', 'actions':['monthly_job_started_one_month_ago_action'], 'config':{'type':'interval', 'unit':'month', 'interval':1, 'start_date':one_month_ago}},
            {'id':'past_4', 'title':'yearly_job_started_one_year_ago', 'actions':['yearly_job_started_one_year_ago_action'], 'config':{'type':'interval', 'unit':'year', 'interval':1, 'start_date':one_year_ago}},
            {'id':'past_5', 'title':'every_2_years_job_started_one_year_ago', 'actions':['every_2_years_job_started_one_year_ago_action'], 'config':{'type':'interval', 'unit':'year', 'interval':2, 'start_date':one_year_ago}},
            {'id':'past_6', 'title':'weekly_job_started_one_week_ago', 'actions':['weekly_job_started_one_week_ago_action'], 'config':{'type':'interval', 'unit':'week', 'interval':1, 'start_date':one_week_ago}}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        self.check_schedules_run(schedule_events, ('expired_date_job', 'every_2_years_job_started_one_year_ago'))

    def test_future_schedules(self):
        one_day_from_now = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(days=1), '%Y-%m-%dT%H:%M:%S.%fZ')
        end_of_month = datetime.datetime.strftime(datetime.datetime(2015,1,31), '%Y-%m-%dT%H:%M:%S.%fZ')
        future_month = datetime.datetime.strftime(datetime.datetime(2017,12,31), '%Y-%m-%dT%H:%M:%S.%fZ')
        future_year = datetime.datetime.strftime(datetime.datetime(2017,1,1), '%Y-%m-%dT%H:%M:%S.%fZ')
        schedule_events = [{'id':'future_1', 'title':'daily_job_starts_one_day_from_now', 'actions':['daily_job_starts_one_day_from_now_action'], 'config':{'type':'interval', 'unit':'day', 'interval':1, 'start_date':one_day_from_now}},
            {'id':'future_2', 'title':'end_of_month_job', 'actions':['end_of_month_job_action'], 'config':{'type':'interval', 'unit':'month', 'interval':1, 'start_date':end_of_month}},
            {'id':'future_3', 'title':'future_month_job', 'actions':['future_month_job_action'], 'config':{'type':'interval', 'unit':'month', 'interval':1, 'start_date':future_month}},
            {'id':'future_4', 'title':'future_year_job', 'actions':['future_year_job_action'], 'config':{'type':'interval', 'unit':'month', 'interval':1, 'start_date':future_year}}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        skip_jobs = [event['title'] for event in schedule_events]
        self.check_schedules_run(schedule_events, skip_jobs)

    def test_reload(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%dT%H:%M:%S.%fZ')
        schedule_events = [{'id':'reload_1', 'title':'date_job', 'actions':['date_job_action'], 'config':{'type':'date', 'start_date':start_date}},
            {'id':'reload_2', 'title':'daily_job', 'actions':['daily_job_action'], 'config':{'type':'interval', 'unit':'day', 'interval':1, 'start_date':start_date}}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        self.check_schedules_run(schedule_events)
        self.test_engine.stop()
        del self.test_engine
        del self.test_client
        self.test_client = TestClient()
        self.test_engine = SchedulerEngine(self.test_client, 'test')
        for event in schedule_events:
            if 'last_run' in event:
                del event['last_run']
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
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%dT%H:%M:%S.%fZ')
        self.schedule_events = [{'id':'delay_1', 'title':'date_job', 'actions':['date_job_action'], 'config':{'type':'date', 'start_date':now}},
            {'id':'delay_2', 'title':'daily_job', 'actions':['daily_job_action'], 'config':{'type':'interval', 'unit':'day', 'interval':1, 'start_date':now}},
            {'id':'delay_3', 'title':'weekly_job', 'actions':['weekly_job_action'], 'config':{'type':'interval', 'unit':'week', 'interval':1, 'start_date':now}},
            {'id':'delay_4', 'title':'monthly_job', 'actions':['monthly_job_action'], 'config':{'type':'interval', 'unit':'month', 'interval':1, 'start_date':now}},
            {'id':'delay_5', 'title':'yearly_job', 'actions':['yearly_job_action'], 'config':{'type':'interval', 'unit':'year', 'interval':1, 'start_date':now}}]
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
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%dT%H:%M:%S.%fZ')
        schedule_events = [{'id':'concurrent_1', 'title':'date_job', 'actions':['date_job_action'], 'config':{'type':'date', 'start_date':now}},
            {'id':'concurrent_1', 'title':'date_job_updated', 'actions':['date_job_action'], 'config':{'type':'date', 'start_date':now}},
            {'id':'concurrent_2', 'title':'daily_job', 'actions':['daily_job_action'], 'config':{'type':'interval', 'unit':'day', 'interval':1, 'start_date':now}},
            {'id':'concurrent_2', 'title':'daily_job_updated', 'actions':['daily_job_action'], 'config':{'type':'interval', 'unit':'day', 'interval':1, 'start_date':now}},
            {'id':'concurrent_3', 'title':'weekly_job', 'actions':['weekly_job_action'], 'config':{'type':'interval', 'unit':'week', 'interval':1, 'start_date':now}},
            {'id':'concurrent_3', 'title':'weekly_job_updated', 'actions':['weekly_job_action'], 'config':{'type':'interval', 'unit':'week', 'interval':1, 'start_date':now}},
            {'id':'concurrent_4', 'title':'monthly_job', 'actions':['monthly_job_action'], 'config':{'type':'interval', 'unit':'month', 'interval':1, 'start_date':now}},
            {'id':'concurrent_4', 'title':'monthly_job_updated', 'actions':['monthly_job_action'], 'config':{'type':'interval', 'unit':'month', 'interval':1, 'start_date':now}},
            {'id':'concurrent_5', 'title':'yearly_job', 'actions':['yearly_job_action'], 'config':{'type':'interval', 'unit':'year', 'interval':1, 'start_date':now}},
            {'id':'concurrent_5', 'title':'yearly_job_updated', 'actions':['yearly_job_action'], 'config':{'type':'interval', 'unit':'year', 'interval':1, 'start_date':now}}]
        for event in schedule_events:
            threading.Thread(target=self.add_schedules, daemon=True, args=([event],)).start()
        #Only half the schedule_events should run since ones with the same id will overwrite previously added ones. Since we don't know what order that will take
        #we just make sure we only check that one of each action has run.
        run_events = {event['id']:event for event in schedule_events if 'id' in event}
        skip_jobs = [event['title'] for event in run_events.values()]
        self.check_schedules_run(schedule_events, skip_jobs)
    
    def test_update_schedules(self):
        start_date = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=60), '%Y-%m-%dT%H:%M:%S.%fZ')
        schedule_events = [{'id':'update_1', 'title':'date_job', 'actions':['date_job_action'], 'config':{'type':'date', 'start_date':start_date}},
            {'id':'update_2', 'title':'daily_job', 'actions':['daily_job_action'], 'config':{'type':'interval', 'unit':'day', 'interval':1, 'start_date':start_date}}]
        self.add_schedules(schedule_events)
        update_schedule_events = [{'id':'update_3', 'title':'date_job_full_update', 'actions':['date_job_full_update_action'], 'config':{'type':'date', 'start_date':start_date}},
            {'id':'update_4', 'title':'daily_job_full_update', 'actions':['daily_job_full_update_action'], 'config':{'type':'interval', 'unit':'day', 'interval':1, 'start_date':start_date}}]
        self.assertTrue(self.test_engine.update_scheduled_events(update_schedule_events))
        self.schedule_events = update_schedule_events
        self.check_schedules_run(update_schedule_events)

    def start_http_server(self):
        self.server = HTTPServer(('localhost', 8000), TestHandler)
        self.server.received = []
        self.server.serve_forever()

    def test_http_notification(self):
        threading.Thread(target=self.start_http_server, daemon=True).start()
        now = datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%dT%H:%M:%S.%fZ')
        schedule_events = [{'id':'http_1', 'title':'date_get_job', 'actions':['date_job_action'],
            'http_push':{'url':'http://localhost:8000', 'method':'GET', 'headers':{'Content-Type':'application/json'}, 'payload':{'test': 'GET request'}},
            'config':{'type':'date', 'start_date':now}},
            {'id':'http_2', 'title':'date_post_job', 'actions':['date_job_action'],
            'http_push':{'url':'http://localhost:8000', 'method':'POST', 'headers':{'Content-Type':'application/json'}, 'payload':{'test': 'POST request'}},
            'config':{'type':'date', 'start_date':now}},
            {'id':'http_3', 'title':'date_put_job', 'actions':['date_job_action'],
            'http_push':{'url':'http://localhost:8000', 'method':'PUT', 'headers':{'Content-Type':'application/json'}, 'payload':{'test': 'PUT request'}},
            'config':{'type':'date', 'start_date':now}},
            {'id':'http_4', 'title':'date_delete_job', 'actions':['date_job_action'],
            'http_push':{'url':'http://localhost:8000', 'method':'DELETE', 'headers':{'Content-Type':'application/json'}, 'payload':{'test': 'DELETE request'}},
            'config':{'type':'date', 'start_date':now}}]
        self.add_schedules(schedule_events)
        self.check_schedules_added(schedule_events)
        self.check_schedules_run(schedule_events)
        self.assertEqual(4, len(self.server.received))
        expected = [event['http_push']['payload'] for event in schedule_events]
        self.assertCountEqual(expected, self.server.received)


if __name__ == '__main__':
    # setDebug()
    setInfo()
    unittest.main()
    # test_suite = unittest.TestSuite()
    # # test_suite.addTest(SchedulerTest('test_current_schedules'))
    # # test_suite.addTest(SchedulerTest('test_future_schedules'))
    # test_suite.addTest(SchedulerTest('test_reload'))
    # # test_suite.addTest(SchedulerTest('test_delayed_load'))
    # # test_suite.addTest(SchedulerTest('test_http_notification'))
    # unittest.TextTestRunner().run(test_suite)

