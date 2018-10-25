from datetime import datetime
from json import dumps, loads
from sqlite3 import connect
from threading import RLock, Thread
from time import sleep

import myDevices.schedule as schedule
from myDevices.requests_futures.sessions import FuturesSession
from myDevices.utils.logger import debug, error, exception, info, logJson, setDebug, warn


class SchedulerEngine(Thread):
    """Class that creates the scheduler and launches scheduled actions"""

    def __init__(self, client, name):
        """Initialize the scheduler and start the scheduler thread
        
        client: the client running the scheduler
        name: name to use for the scheduler thread"""
        self.connection = connect('/etc/myDevices/agent.db', check_same_thread = False)
        self.cursor = self.connection.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS scheduled_events (id TEXT PRIMARY KEY, event TEXT)')
        Thread.__init__(self, name=name)
        self.mutex = RLock()
        self.schedule_items = {}
        self.client = client
        self.running = False
        self.load_schedule()
        self.start()

    def __del__(self):
        """Delete scheduler object"""
        try:
            self.connection.close()
        except:
            exception('Error deleting SchedulerEngine')

    def load_schedule(self):
        """Load saved scheduler events from the database"""
        with self.mutex:
            self.cursor.execute('SELECT * FROM scheduled_events')
            results = self.cursor.fetchall()
            for row in results:
                self.add_scheduled_event(loads(row[1]), False)
        return True

    def add_scheduled_event(self, event, insert = False):
        """Add a scheduled event to run via the scheduler
        
        event: the scheduled event to add
        insert: if True add the event to the database, otherwise just add it to the running scheduler"""
        debug('Add scheduled event')
        result = False
        try:
            if event['id'] is None:
                raise ValueError('No id specified for scheduled event: {}'.format(event))
            schedule_item = {'event': event, 'job': None}
            with self.mutex:    
                try:
                    if event['id'] not in self.schedule_items:                   
                        if insert == True:
                            self.add_database_record(event['id'], event)
                        result = self.create_job(schedule_item)                        
                        if result == True:
                            self.schedule_items[event['id']] = schedule_item
                    else:
                        result = self.update_scheduled_event(event)
                except:
                    exception('Error adding scheduled event')
        except:
            exception('Failed to add scheduled event')
        return result

    def update_scheduled_event(self, event):
        """Update an existing scheduled event
        
        event: the scheduled event to update"""
        debug('Update scheduled event')
        result = False
        try:
            schedule_item = {'event': event, 'job': None}
            with self.mutex:
                try:
                    old_item = self.schedule_items[event['id']]
                    schedule.cancel_job(old_item['job'])
                    result = self.create_job(schedule_item)
                    debug('Update scheduled event result: {}'.format(result))
                    if result == True:
                        self.update_database_record(event['id'], event)
                        self.schedule_items[event['id']] = schedule_item
                except KeyError:
                    debug('Old schedule with id = {} not found'.format(event['id']))
        except:
            exception('Failed to update scheduled event')
        return result

    def remove_scheduled_event(self, event):
        """Remove an event that has been scheduled
        
        event: the event to remove"""
        debug('Remove scheduled event')
        return self.remove_scheduled_item_by_id(event['id'])

    def update_scheduled_events(self, events):
        """Update all scheduled events
        
        events: list of all the new events to schedule"""
        logJson('Update schedules:  {}'.format(events))
        debug('Updating schedules')
        try:
            with self.mutex:
                self.remove_scheduled_events()
                for event in events:
                    self.add_scheduled_event(event, True)
        except:
            exception('Failed to update scheduled events')
            result = False
        return True

    def get_scheduled_events(self):
        """Return a list of all scheduled events"""
        events = []
        try:
            with self.mutex:
                events = [schedule_item['event'] for schedule_item in self.schedule_items.values()]
                for event in events:
                    try:
                        # Don't include last run value that is only used locally.
                        del event['last_run']
                    except:
                        pass
        except:
            exception('Failed to get scheduled events')
        return events

    def remove_scheduled_events(self):
        """Remove all scheduled events from the scheduler"""
        try:
            with self.mutex:
                schedule.clear()
                self.schedule_items.clear()
                self.remove_all_database_records()
        except:
            exception('Failed to remove scheduled events')
            return False
        return True

    def remove_scheduled_item_by_id(self, remove_id):
        """Remove a scheduled item with the specified id
        
        id: id specifying the item to remove"""
        with self.mutex:
            if remove_id in self.schedule_items:
                try:
                    schedule_item = self.schedule_items[remove_id]
                    schedule.cancel_job(schedule_item['job'])
                    del self.schedule_items[remove_id]
                    self.remove_database_record(remove_id)
                    return True
                except KeyError:
                    warn('Key error removing scheduled item: {}'.format(remove_id))
        error('Remove id not found: {}'.format(remove_id))
        return False
        
    def create_job(self, schedule_item):
        """Create a job to run a scheduled item
        
        schedule_item: the item containing the event to be run at the scheduled time"""
        debug('Create job: {}'.format(schedule_item))
        try:
            with self.mutex:
                config = schedule_item['event']['config']
                if config['type'] == 'date':
                    schedule_item['job'] = schedule.once().at(config['start_date'])
                if config['type'] == 'interval':
                    if config['unit'] == 'hour':
                        schedule_item['job'] = schedule.every(config['interval'], config['start_date']).hours
                    if config['unit'] == 'minute':
                        schedule_item['job'] = schedule.every(config['interval'], config['start_date']).minutes
                    if config['unit'] == 'day':
                        schedule_item['job'] = schedule.every(config['interval'], config['start_date']).days.at(config['start_date'])
                    if config['unit'] == 'week':
                        schedule_item['job'] = schedule.every(config['interval'], config['start_date']).weeks.at(config['start_date'])
                    if config['unit'] == 'month':
                        schedule_item['job'] = schedule.every(config['interval'], config['start_date']).months.at(config['start_date'])
                    if config['unit'] == 'year':
                        schedule_item['job'] = schedule.every(config['interval'], config['start_date']).years.at(config['start_date'])
                if 'last_run' in schedule_item['event']:
                    schedule_item['job'].set_last_run(schedule_item['event']['last_run'])
                schedule_item['job'].do(self.run_scheduled_item, schedule_item)
        except:
            exception('Failed setting up scheduler')
            return False
        return True

    def run_scheduled_item(self, schedule_item):
        """Run an item that has been scheduled
        
        schedule_item: the item containing the event to run"""
        debug('Process action')
        if not schedule_item:
            error('No scheduled item to run')
            return
        result = True
        event = schedule_item['event']
        config = event['config']
        event['last_run'] = datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M')
        with self.mutex:
            self.update_database_record(event['id'], event)
        action_executed = False
        for action in event['actions']:
            info('Executing scheduled action: {}'.format(action))
            result = self.client.RunAction(action)           
            if result == False:
                error('Failed to execute action: {}'.format(action))
            else:
                action_executed = True
        if config['type'] == 'date' and result == True:
            with self.mutex:
                schedule.cancel_job(schedule_item['job'])
        if action_executed and 'http_push' in event:
            info('Scheduler making HTTP request')
            http_push = event['http_push']
            try:
                future = None
                session = FuturesSession(max_workers=1)
                session.headers = http_push['headers']
                if http_push['method'] == 'GET':
                    future = session.get(http_push['url'])
                if http_push['method'] == 'POST':
                    future = session.post(http_push['url'], dumps(http_push['payload']))
                if http_push['method'] == 'PUT':
                    future = session.put(http_push['url'], dumps(http_push['payload']))
                if http_push['method'] == 'DELETE':
                    future = session.delete(http_push['url'])
            except Exception as ex:
                error('Scheduler HTTP request exception: {}'.format(ex))
                return None
            try:
                response = future.result(30)
                info('Scheduler HTTP response: {}'.format(response))
            except:
                pass

    def add_database_record(self, id, event):
        """Add a scheduled event to the database
        
        id: id of the scheduled event
        event: the scheduled event"""
        debug('Add database record')
        result = False
        with self.mutex:
            self.cursor.execute('INSERT INTO scheduled_events VALUES (?,?)', (id, dumps(event)))
            self.connection.commit()
            result = self.cursor.lastrowid
        debug('Add database record result: {}'.format(result))
        return result
        
    def update_database_record(self, id, event):
        """Update the database with the scheduled event
        
        id: id of the scheduled event
        event: the scheduled event"""
        debug('Update database record')
        result = True
        try:
            with self.mutex:
                self.cursor.execute('UPDATE scheduled_events SET event = ? WHERE id = ?', (dumps(event), id))
                self.connection.commit()
        except:
            exception('Error updating database')
            result = False
        debug('Update database record result: {}'.format(result))
        return result

    def remove_database_record(self, id):
        """Remove a scheduled event from the database
        
        id: id of the scheduled event"""
        debug('Remove database record')
        result = True
        try:
            with self.mutex:
                self.cursor.execute('DELETE FROM scheduled_events WHERE id = ?', (id,))
                self.connection.commit()
        except:
            result = False
        debug('Remove database record result: {}'.format(result))
        return result

    def remove_all_database_records(self):
        """Remove all scheduled events from the database"""        
        result = True
        debug('Remove all database records')
        try:
            with self.mutex:
                self.cursor.execute('DELETE FROM scheduled_events')
                self.connection.commit()
        except:
            result = False
        debug('Remove all database records result: {}'.format(result))
        return result

    def run(self):
        """Start the scheduler thread"""
        self.running = True
        while self.running:
            try:
                with self.mutex:
                    schedule.run_pending()
            except:
                exception("SchedulerEngine run, unexpected error")
            sleep(1)

    def stop(self):
        """Stop the scheduler"""
        self.running = False
