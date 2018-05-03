from threading import Thread, RLock
from myDevices.utils.logger import exception, info, warn, error, debug, setDebug, logJson
import myDevices.schedule as schedule
from time import sleep
from json import dumps, loads, JSONEncoder
from myDevices.cloud.dbmanager import DbManager
from datetime import datetime
from jsonpickle import encode

def ToJson(object):
    returnValue = "{}"
    try:

        returnValue = encode(object, unpicklable=False, make_refs=False)
    except:
        exception('ToJson Failed')
    return returnValue
#{
#   "id":"some_unique_id",
#   "type":"date/interval",
#   "unit":"minute/hour/day/week/month/year",
#   "interval":1,
#   "weekday":"monday/tuesday/...",
#   "start_date":"date and hour",
#   "end_date":"date and hour",
#   "title":"sometext",
#   "notify":"yes/no",
#   "actions":
#   [
#   ]
#} 

#AccountId = None

class ScheduleItemEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, schedule.Job):
            return None
        if isinstance(obj, ScheduleItem):
            return {key: value for key, value in obj.__dict__.items() if value is not None and not isinstance(value, schedule.Job)}
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)
class ScheduleItem():#handlers.BaseHandler
    def __init__(self, jsonData):
        debug('SheduleItem::__init__: ' + str(jsonData) )
        self.type = jsonData['type']
        self.job = None
        self.actions = []
        self.start_date = None
        self.end_date = None
        self.last_run = None
        if 'start_date' in jsonData:
            self.start_date = jsonData['start_date']
        if 'end_date' in jsonData:
            self.end_date = jsonData['end_date']
        if 'last_run' in jsonData:
            self.last_run = jsonData['last_run']
        #if 'AccountId' in jsonData:
        #    AccountId = jsonData['AccountId']
        self.notify = jsonData['notify']
        self.title = jsonData['title']
        self.interval = None
        self.unit = None    
        self.weekday = None
        self.id = None
        if 'id' in jsonData:
            self.id = jsonData['id']
        if self.type == 'interval':
            self.interval = 1
            if 'interval' in jsonData:
                self.interval = jsonData['interval']
            self.unit = jsonData['unit']    
            #self.weekday = jsonData['weekday']
        if 'actions' in jsonData:
            for action in jsonData['actions']:
                self.actions.append(action)    
        #def __reduce__(self):
        #    return ScheduleItem, self._get_args()
    def __repr__(self):    
        return self.title
    def to_JSON(self):
        return dumps(self, cls=ScheduleItemEncoder)
    def to_dict(self):
        return {key: value for key, value in vars(self).items() if not isinstance(value, schedule.Job)}

class SchedulerEngine(Thread):
    def __init__(self, client, name):
        Thread.__init__(self, name=name)
        self.mutex = RLock()
        #failover cases: keep last run and next run times 
        #if the scheduler is not running at a specific time it should be checked
        self.schedules={}
        self.testIndex = 0
        self.client = client
        self.Continue = False
        self.tablename = 'scheduled_settings'
        #at the end load data
        self.LoadData()
        self.start()
        #handlers.register(ScheduleItem, handlers.SimpleReduceHandler)
    def LoadData(self):
        with self.mutex:
            results = DbManager.Select(self.tablename)
            if results:
                for row in results:
                    #info('Row: ' + str(row))
                    #for each item already present in db add call AddScheduledItem with insert false
                    self.AddScheduledItem(loads(row[1]), False)
        return True
    def AddScheduledItem(self, jsonData, insert = False):
        #add schedule to both memory and db
        debug('')
        retVal = False
        try:
            scheduleItem = ScheduleItem(jsonData)
            if scheduleItem.id is None:
                raise ValueError('No id specified for scheduled item: {}'.format(jsonData))
            with self.mutex:    
                try:
                    if scheduleItem.id not in self.schedules:                   
                        if insert == True:
                            self.AddDbItem(scheduleItem.id, ToJson(jsonData))
                        info('Setup item: ' + str(scheduleItem.to_dict()))
                        retVal = self.Setup(scheduleItem)                        
                        if retVal == True:
                            self.schedules[scheduleItem.id] = scheduleItem
                    else:
                        retVal = self.UpdateScheduledItem(jsonData)
                except:
                    exception('Error adding scheduled item')
        except:
            exception('AddScheduledItem Failed')
        return retVal
    def UpdateScheduledItem(self, jsonData):
        debug('')
        retVal = False
        try:
            scheduleItemNew = ScheduleItem(jsonData)
            with self.mutex:
                try:
                    scheduleItemOld = self.schedules[scheduleItemNew.id]
                    schedule.cancel_job(scheduleItemOld.job)
                except KeyError:
                    debug('Old schedule with id = {} not found'.format(scheduleItemNew.id))
                retVal = self.Setup(scheduleItemNew)
                if retVal == True:
                    self.UpdateDbItem(ToJson(jsonData), scheduleItemNew.id)
                    self.schedules[scheduleItemNew.id] = scheduleItemNew
        except:
            exception('UpdateScheduledItem Failed')
        return retVal
    def Setup(self,scheduleItem):
        try:
            with self.mutex:
                if scheduleItem.type == 'date':
                    scheduleItem.job = schedule.once().at(str(scheduleItem.start_date))
                if scheduleItem.type == 'interval':
                    if scheduleItem.unit == 'hour':
                        scheduleItem.job = schedule.every(int(scheduleItem.interval), scheduleItem.start_date).hours
                    if scheduleItem.unit == 'minute':
                        scheduleItem.job = schedule.every(int(scheduleItem.interval), scheduleItem.start_date).minutes
                    if scheduleItem.unit == 'day':
                        scheduleItem.job = schedule.every(scheduleItem.interval, scheduleItem.start_date).days.at(scheduleItem.start_date)
                    if scheduleItem.unit == 'week':
                        scheduleItem.job = schedule.every(scheduleItem.interval, scheduleItem.start_date).weeks.at(scheduleItem.start_date)
                    if scheduleItem.unit == 'month':
                        scheduleItem.job = schedule.every(scheduleItem.interval, scheduleItem.start_date).months.at(scheduleItem.start_date)
                    if scheduleItem.unit == 'year':
                        scheduleItem.job = schedule.every(scheduleItem.interval, scheduleItem.start_date).years.at(scheduleItem.start_date)
                scheduleItem.job.set_last_run(scheduleItem.last_run)
                scheduleItem.job.do(self.ProcessAction, scheduleItem)
        except:
            exception('Failed setting up scheduler')
            return False
        return True
    def ProcessAction(self, scheduleItem):
        debug('')
        if scheduleItem is None:
            error('ProcessAction with empty schedule')
            return
        # if scheduleItem.job.should_run() == False:
        #     return
        statusSuccess = True
        scheduleItem.last_run = datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M')
        with self.mutex:
            self.UpdateDbItem(scheduleItem.to_JSON(), scheduleItem.id)
        #TODO
        #all this scheduler notification should be put in a db and if it was not possible to submit add a checker for sending notifications to cloud
        #right now is a workaround in order to submit
        debug('Notification: ' + str(scheduleItem.notify))
        if scheduleItem.notify:
            body = 'Scheduler ' + scheduleItem.title + ' ran with success: ' + str(statusSuccess) + ' at UTC ' + str(datetime.utcnow())
            subject = scheduleItem.title 
            #build an array of device names
            #if this fails to be sent, save it in the DB and resubmit it
            runStatus = False #self.client.SendNotification(scheduleItem.notify, subject, body)
            sleep(1)
            if runStatus == False:
                error('Notification ' + str(scheduleItem.notify) + ' was not sent')
        for action in scheduleItem.actions:
            #call cloudserver 
            runStatus = self.client.RunAction(action)
            info('Schedule executing action: ' + str(action))
            if runStatus == False:
                error('Action: ' + str(action) + ' failed')
                statusSuccess = False
        if scheduleItem.type == 'date' and statusSuccess == True:
            with self.mutex:
                schedule.cancel_job(scheduleItem.job)
    #remove schedule from both memory and db
    def RemoveScheduledItem(self, removeItem):
        debug('')
        return self.RemoveScheduledItemById(removeItem['id'])
    #remove schedule with specified id from both memory and db
    def RemoveScheduledItemById(self, id):
        with self.mutex:
            if id in self.schedules:
                try:
                    scheduleItem = self.schedules[id]
                    schedule.cancel_job(scheduleItem.job)
                    del self.schedules[id]
                    self.RemoveDbItem(scheduleItem.id)
                    return True
                except KeyError:
                    warn('RemoveScheduledItem key error: ' + str(Id))
        error('RemoveScheduledItem id not found: ' + str(id))
        return False
    #remove all scheduled items
    def RemoveSchedules(self):
        try:
            with self.mutex:
                schedule.clear()
                self.schedules.clear()
                self.RemoveAllDbItems()
        except:
            exception('RemoveSchedules failed')
            return False
        return True
    #retrieve schedules from memory
    def GetSchedules(self):
        jsonSchedules = []
        try:
            with self.mutex:
                for scheduleItem in self.schedules:
                    jsonSchedules.append(self.schedules[scheduleItem].to_dict())
        except:
            exception('GetSchedules Failed')
        return jsonSchedules
    #update all schedules
    def UpdateSchedules(self, jsonData):
        retValue = True
        logJson('UpdateSchedules' + str(jsonData), 'schedules')
        info('Schedules updated from cloud...')
        try:
            with self.mutex:
                jsonSchedules = jsonData['Schedules']
                self.RemoveSchedules()
                for item in jsonSchedules:
                    self.AddScheduledItem(item['Schedule'], True)
        except:
            exception('UpdateSchedules Failed')
            retValue = False
        return retValue
    #db items
    def UpdateDbItem(self, jsonData, id):
        debug('')
        bVal = True
        try:
            setClause =  'data = ?'
            whereClause = 'id = ?'
            with self.mutex:
                DbManager.Update(self.tablename, setClause, jsonData, whereClause, id)
        except:
            bVal = False
        return bVal
    def AddDbItem(self, id, jsonData):
        debug('')
        bVal = False
        with self.mutex:
            bVal= DbManager.Insert(self.tablename, id, jsonData)
        return bVal
    def RemoveDbItem(self, id):
        bVal = True
        try:
            with self.mutex:
                DbManager.Delete(self.tablename, id)
        except:
            bVal = False
        return bVal
    def RemoveAllDbItems(self):
        bVal = True
        try:
            with self.mutex:
                DbManager.DeleteAll(self.tablename)
        except:
            bVal = False
        return bVal
    def stop(self):
        #debug('Scheduler stop')
        self.Continue = False
    def run(self):
        self.Continue = True
        #debug('Scheduler running')
        while self.Continue:
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
