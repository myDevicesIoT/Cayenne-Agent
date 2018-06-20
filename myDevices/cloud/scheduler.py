from threading import Thread, RLock
from myDevices.utils.logger import exception, info, warn, error, debug, setDebug, logJson
import myDevices.schedule as schedule
from time import sleep
from json import dumps, loads, JSONEncoder
from myDevices.cloud.dbmanager import DbManager
from datetime import datetime


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
        Thread.__init__(self, name=name)
        self.mutex = RLock()
        #failover cases: keep last run and next run times 
        #if the scheduler is not running at a specific time it should be checked
        self.schedules={}
        self.testIndex = 0
        self.client = client
        self.running = False
        self.tablename = 'scheduled_settings'
        #at the end load data
        self.load_data()
        self.start()
        
    def load_data(self):
        """Load saved scheduler data from the database"""
        with self.mutex:
            results = DbManager.Select(self.tablename)
            if results:
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
        retVal = False
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
                        retVal = self.setup(schedule_item)                        
                        if retVal == True:
                            self.schedules[schedule_item.id] = schedule_item
                    else:
                        retVal = self.update_scheduled_item(json_data)
                except:
                    exception('Error adding scheduled item')
        except:
            exception('AddScheduledItem Failed')
        return retVal

    def update_scheduled_item(self, json_data):
        """Update an existing scheduled item
        
        json_data: JSON object representing the scheduled item to update"""
        debug('')
        retVal = False
        try:
            scheduleItemNew = ScheduleItem(json_data)
            with self.mutex:
                try:
                    scheduleItemOld = self.schedules[scheduleItemNew.id]
                    schedule.cancel_job(scheduleItemOld.job)
                except KeyError:
                    debug('Old schedule with id = {} not found'.format(scheduleItemNew.id))
                retVal = self.setup(scheduleItemNew)
                if retVal == True:
                    self.update_database_item(dumps(json_data), scheduleItemNew.id)
                    self.schedules[scheduleItemNew.id] = scheduleItemNew
        except:
            exception('UpdateScheduledItem Failed')
        return retVal

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

    def remove_scheduled_item(self, removeItem):
        """Remove an item that has been scheduled
        
        removeItem: a JSON object specifying the item to remove"""
        debug('')
        return self.remove_scheduled_item_by_id(removeItem['id'])

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
        jsonSchedules = []
        try:
            with self.mutex:
                for schedule_item in self.schedules:
                    jsonSchedules.append(self.schedules[schedule_item].to_dict())
        except:
            exception('GetSchedules Failed')
        return jsonSchedules

    def update_schedules(self, json_data):
        """Update all scheduled items
        
        json_data: JSON containing a list of all the new items to schedule"""
        result = True
        logJson('UpdateSchedules' + str(json_data), 'schedules')
        info('Updating schedules')
        try:
            with self.mutex:
                jsonSchedules = json_data['Schedules']
                self.remove_schedules()
                for item in jsonSchedules:
                    self.add_scheduled_item(item['Schedule'], True)
        except:
            exception('UpdateSchedules Failed')
            result = False
        return result

    def update_database_item(self, json_data, id):
        """Update the database with the scheduled item
        
        json_data: JSON containing the scheduled item
        id: id of the scheduled item"""
        debug('')
        result = True
        try:
            setClause =  'data = ?'
            whereClause = 'id = ?'
            with self.mutex:
                DbManager.Update(self.tablename, setClause, json_data, whereClause, id)
        except:
            result = False
        return result

    def add_database_item(self, id, json_data):
        """Add a scheduled item to the database
        
        id: id of the scheduled item
        json_data: JSON containing the scheduled item"""
        debug('')
        result = False
        with self.mutex:
            result = DbManager.Insert(self.tablename, id, json_data)
        return result

    def remove_database_item(self, id):
        """Remove a scheduled item from the database
        
        id: id of the scheduled item"""
        result = True
        try:
            with self.mutex:
                DbManager.Delete(self.tablename, id)
        except:
            result = False
        return result

    def remove_all_database_items(self):
        """Remove all scheduled items from the database"""        
        result = True
        try:
            with self.mutex:
                DbManager.DeleteAll(self.tablename)
        except:
            result = False
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
                exception("SchedulerEngine run, Unexpected error")
            sleep(1)


class TestClient():
    def __init__(self):
        print('test client init')
    def RunAction(self, action):
        print('RunAction: ' + action)
    def SendNotification(self, notification):
        print('SendNotification: ' + notification)
