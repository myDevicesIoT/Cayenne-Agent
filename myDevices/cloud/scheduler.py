from datetime import datetime
from json import JSONEncoder, dumps, loads
from sqlite3 import connect
from threading import RLock, Thread
from time import sleep

import myDevices.schedule as schedule
from myDevices.utils.logger import debug, error, exception, info, logJson, setDebug, warn


class ScheduleItemEncoder(JSONEncoder):
    """Serialize a ScheduleItem object to JSON"""

    def default(self, obj):
        """Default function for serializing object
        
        obj: object to encode to JSON"""
        if isinstance(obj, schedule.Job):
            return None
        if isinstance(obj, ScheduleItem):
            return {key: value for key, value in obj.__dict__.items() if value is not None and not isinstance(value, schedule.Job)}
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)


class ScheduleItem():
    """Class for creating a scheduled action"""

    def __init__(self, json_data):
        """Initializes a scheduled item from a JSON object
        
        json_data: JSON object with scheduled item data

        Example JSON format::

            {
                "id":"some_unique_id",
                "type":"date/interval",
                "unit":"minute/hour/day/week/month/year",
                "interval":1,
                "start_date":"date and hour",
                "end_date":"date and hour",
                "title":"sometext",
                "notify":"yes/no",
                "actions":
                [
                ]
            } 
        """
        debug('ScheduleItem::__init__: ' + str(json_data) )
        self.type = json_data['type']
        self.job = None
        self.actions = []
        self.start_date = None
        self.end_date = None
        self.last_run = None
        if 'start_date' in json_data:
            self.start_date = json_data['start_date']
        if 'end_date' in json_data:
            self.end_date = json_data['end_date']
        if 'last_run' in json_data:
            self.last_run = json_data['last_run']
        self.notify = json_data['notify']
        self.title = json_data['title']
        self.interval = None
        self.unit = None    
        self.id = None
        if 'id' in json_data:
            self.id = json_data['id']
        if self.type == 'interval':
            self.interval = 1
            if 'interval' in json_data:
                self.interval = json_data['interval']
            self.unit = json_data['unit']    
        if 'actions' in json_data:
            for action in json_data['actions']:
                self.actions.append(action)    

    def __repr__(self):
        """Return title of scheduled item"""
        return self.title

    def to_json(self):
        """Return scheduled item as a JSON object"""
        return dumps(self, cls=ScheduleItemEncoder)

    def to_dict(self):
        """Return scheduled item as a dict"""
        return {key: value for key, value in vars(self).items() if not isinstance(value, schedule.Job)}


class SchedulerEngine(Thread):
    """Class that creates the scheduler and launches scheduled actions"""

    def __init__(self, client, name):
        """Initialize the scheduler and start the scheduler thread
        
        client: the client running the scheduler
        name: name to use for the scheduler thread"""
        self.connection = connect('/etc/myDevices/agent.db', check_same_thread = False)
        self.cursor = self.connection.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS scheduled_items (id TEXT PRIMARY KEY, data TEXT)')
        Thread.__init__(self, name=name)
        self.mutex = RLock()
        #failover cases: keep last run and next run times 
        #if the scheduler is not running at a specific time it should be checked
        self.schedules={}
        self.testIndex = 0
        self.client = client
        self.running = False
        #at the end load data
        self.load_data()
        self.start()

    def __del__(self):
        """Delete scheduler object"""
        try:
            self.connection.close()
        except:
            exception('Error deleting SchedulerEngine')

    def load_data(self):
        """Load saved scheduler data from the database"""
        with self.mutex:
            self.cursor.execute('SELECT * FROM scheduled_items')
            results = self.cursor.fetchall()
            for row in results:
                #info('Row: ' + str(row))
                #for each item already present in db add call AddScheduledItem with insert false
                self.add_scheduled_item(loads(row[1]), False)
        return True

    def add_scheduled_item(self, json_data, insert = False):
        """Add a scheduled item to run via the scheduler
        
        json_data: JSON object representing the scheduled item to add
        insert: if True add the item to the database, otherwise just add it to the running scheduler"""
        debug('')
        result = False
        try:
            schedule_item = ScheduleItem(json_data)
            if schedule_item.id is None:
                raise ValueError('No id specified for scheduled item: {}'.format(json_data))
            with self.mutex:    
                try:
                    if schedule_item.id not in self.schedules:                   
                        if insert == True:
                            self.add_database_item(schedule_item.id, dumps(json_data))
                        info('Setup item: ' + str(schedule_item.to_dict()))
                        result = self.setup(schedule_item)                        
                        if result == True:
                            self.schedules[schedule_item.id] = schedule_item
                    else:
                        result = self.update_scheduled_item(json_data)
                except:
                    exception('Error adding scheduled item')
        except:
            exception('AddScheduledItem failed')
        return result

    def update_scheduled_item(self, json_data):
        """Update an existing scheduled item
        
        json_data: JSON object representing the scheduled item to update"""
        debug('Update scheduled item')
        result = False
        try:
            scheduleItemNew = ScheduleItem(json_data)
            with self.mutex:
                try:
                    scheduleItemOld = self.schedules[scheduleItemNew.id]
                    schedule.cancel_job(scheduleItemOld.job)
                except KeyError:
                    debug('Old schedule with id = {} not found'.format(scheduleItemNew.id))
                result = self.setup(scheduleItemNew)
                debug('Update scheduled item result: {}'.format(result))
                if result == True:
                    self.update_database_item(dumps(json_data), scheduleItemNew.id)
                    self.schedules[scheduleItemNew.id] = scheduleItemNew
        except:
            exception('UpdateScheduledItem failed')
        return result

    def setup(self, schedule_item):
        """Setup a job to run a scheduled item
        
        schedule_item: a ScheduleItem instance representing the item to run"""
        try:
            with self.mutex:
                if schedule_item.type == 'date':
                    schedule_item.job = schedule.once().at(str(schedule_item.start_date))
                if schedule_item.type == 'interval':
                    if schedule_item.unit == 'hour':
                        schedule_item.job = schedule.every(int(schedule_item.interval), schedule_item.start_date).hours
                    if schedule_item.unit == 'minute':
                        schedule_item.job = schedule.every(int(schedule_item.interval), schedule_item.start_date).minutes
                    if schedule_item.unit == 'day':
                        schedule_item.job = schedule.every(schedule_item.interval, schedule_item.start_date).days.at(schedule_item.start_date)
                    if schedule_item.unit == 'week':
                        schedule_item.job = schedule.every(schedule_item.interval, schedule_item.start_date).weeks.at(schedule_item.start_date)
                    if schedule_item.unit == 'month':
                        schedule_item.job = schedule.every(schedule_item.interval, schedule_item.start_date).months.at(schedule_item.start_date)
                    if schedule_item.unit == 'year':
                        schedule_item.job = schedule.every(schedule_item.interval, schedule_item.start_date).years.at(schedule_item.start_date)
                schedule_item.job.set_last_run(schedule_item.last_run)
                schedule_item.job.do(self.process_action, schedule_item)
        except:
            exception('Failed setting up scheduler')
            return False
        return True

    def process_action(self, schedule_item):
        """Process an item that has been scheduled
        
        schedule_item: a ScheduleItem instance representing the item to process and run"""
        debug('')
        if schedule_item is None:
            error('ProcessAction with empty schedule')
            return
        # if schedule_item.job.should_run() == False:
        #     return
        statusSuccess = True
        schedule_item.last_run = datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M')
        with self.mutex:
            self.update_database_item(schedule_item.to_json(), schedule_item.id)
        #TODO
        #all this scheduler notification should be put in a db and if it was not possible to submit add a checker for sending notifications to cloud
        #right now is a workaround in order to submit
        debug('Notification: ' + str(schedule_item.notify))
        if schedule_item.notify:
            body = 'Scheduler ' + schedule_item.title + ' ran with success: ' + str(statusSuccess) + ' at UTC ' + str(datetime.utcnow())
            subject = schedule_item.title 
            #build an array of device names
            #if this fails to be sent, save it in the DB and resubmit it
            runStatus = False #self.client.SendNotification(schedule_item.notify, subject, body)
            sleep(1)
            if runStatus == False:
                error('Notification ' + str(schedule_item.notify) + ' was not sent')
        for action in schedule_item.actions:
            #call cloudserver 
            runStatus = self.client.RunAction(action)
            info('Schedule executing action: ' + str(action))
            if runStatus == False:
                error('Action: ' + str(action) + ' failed')
                statusSuccess = False
        if schedule_item.type == 'date' and statusSuccess == True:
            with self.mutex:
                schedule.cancel_job(schedule_item.job)

    def remove_scheduled_item(self, remove_item):
        """Remove an item that has been scheduled
        
        remove_item: a JSON object specifying the item to remove"""
        debug('')
        return self.remove_scheduled_item_by_id(remove_item['id'])

    def remove_scheduled_item_by_id(self, id):
        """Remove a scheduled item with the specified id
        
        id: id specifying the item to remove"""
        with self.mutex:
            if id in self.schedules:
                try:
                    schedule_item = self.schedules[id]
                    schedule.cancel_job(schedule_item.job)
                    del self.schedules[id]
                    self.remove_database_item(schedule_item.id)
                    return True
                except KeyError:
                    warn('RemoveScheduledItem key error: ' + str(Id))
        error('RemoveScheduledItem id not found: ' + str(id))
        return False

    def remove_schedules(self):
        """Remove all scheduled items from the scheduler"""
        try:
            with self.mutex:
                schedule.clear()
                self.schedules.clear()
                self.remove_all_database_items()
        except:
            exception('RemoveSchedules failed')
            return False
        return True

    def get_schedules(self):
        """Return a list of all scheduled items"""
        schedules = []
        try:
            with self.mutex:
                for schedule_item in self.schedules:
                    schedules.append(self.schedules[schedule_item].to_dict())
        except:
            exception('GetSchedules failed')
        return schedules

    def update_schedules(self, schedule_items):
        """Update all scheduled items
        
        schedule_items: list of all the new items to schedule"""
        result = True
        logJson('Update schedules:  {}'.format(schedule_items))
        debug('Updating schedules')
        try:
            with self.mutex:
                self.remove_schedules()
                for item in schedule_items:
                    self.add_scheduled_item(item, True)
        except:
            exception('UpdateSchedules failed')
            result = False
        return result

    def update_database_item(self, json_data, id):
        """Update the database with the scheduled item
        
        json_data: JSON containing the scheduled item
        id: id of the scheduled item"""
        debug('Update database item')
        result = True
        try:
            with self.mutex:
                self.cursor.execute('UPDATE scheduled_items SET data = ? WHERE id = ?', (json_data, id))
                self.connection.commit()
        except:
            exception('Error updating database item')
            result = False
        debug('Update database item result: {}'.format(result))
        return result

    def add_database_item(self, id, json_data):
        """Add a scheduled item to the database
        
        id: id of the scheduled item
        json_data: JSON containing the scheduled item"""
        debug('Add database item')
        result = False
        with self.mutex:
            self.cursor.execute('INSERT INTO scheduled_items VALUES (?,?)', (id, json_data))
            self.connection.commit()
            result = self.cursor.lastrowid
        debug('Add database item result: {}'.format(result))
        return result

    def remove_database_item(self, id):
        """Remove a scheduled item from the database
        
        id: id of the scheduled item"""
        debug('Remove database item')
        result = True
        try:
            with self.mutex:
                self.cursor.execute('DELETE FROM scheduled_items WHERE id = ?', (id,))
                self.connection.commit()
        except:
            result = False
        debug('Remove database item result: {}'.format(result))
        return result

    def remove_all_database_items(self):
        """Remove all scheduled items from the database"""        
        result = True
        debug('Remove all database items')
        try:
            with self.mutex:
                self.cursor.execute('DELETE FROM scheduled_items')
                self.connection.commit()
        except:
            result = False
        debug('Remove all database items result: {}'.format(result))
        return result

    def stop(self):
        """Stop the scheduler"""
        #debug('Scheduler stop')
        self.running = False

    def run(self):
        """Start the scheduler thread"""
        self.running = True
        #debug('Scheduler running')
        while self.running:
            try:
                with self.mutex:
                    schedule.run_pending()
            except:
                exception("SchedulerEngine run, unexpected error")
            sleep(1)


class TestClient():
    def __init__(self):
        print('test client init')
    def RunAction(self, action):
        print('RunAction: ' + action)
    def SendNotification(self, notification):
        print('SendNotification: ' + notification)
