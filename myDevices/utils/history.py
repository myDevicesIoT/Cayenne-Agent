from myDevices.utils.logger import exception, info, warn, error, debug, setDebug, logJson
from json import loads, dumps
from time import time
from datetime import datetime, timedelta
from sqlite3 import connect
from operator import itemgetter
from os import rename
from sys import argv

class History:
    NOT_READY = 'Not Ready'
    READY = 'Ready'
    SENDING = 'Sending'
    SENT = 'Sent'
    RUNNING = 'Running'
    HOUR = 'Hour'
    DAY = 'Day'
    WEEK = 'Week'
    MONTH = 'Month'
    YEAR = 'Year'
    
    def __init__(self):
        try:
            self.count = 0
            self.avg_values = {}
            self.count_sensor = {}
            self.count_sensor['SensorsInfo'] = {}
            self.id = None
            self.start_time = time()
            self.end_time = None
            self.connection = connect('/etc/myDevices/agent.db', check_same_thread = False)
            self.cursor = self.connection.cursor()
            self.cursor.execute('PRAGMA table_info(historical_averages)')
            actual_columns = [column[1] for column in self.cursor.fetchall()]
            # required_columns = ['id', 'data', 'count', 'start', 'end', 'interval', 'send', 'count_sensor']
            # if actual_columns != required_columns:
            #     try:
            #         warn('historical_averages table columns {} do not match required columns {}, dropping table'.format(actual_columns, required_columns))
            #         self.cursor.execute('DROP TABLE historical_averages')
            #         self.connection.commit()
            #     except:
            #         pass
            # self.cursor.execute('CREATE TABLE IF NOT EXISTS historical_averages (id INTEGER PRIMARY KEY, data TEXT, count INTEGER, start TIMESTAMP, end TIMESTAMP, interval TEXT, send TEXT, count_sensor TEXT)')
            self.cursor.execute('SELECT * FROM historical_averages WHERE interval = ? ORDER BY end DESC LIMIT 1', (History.RUNNING,))
            results = self.cursor.fetchall()
            for row in results:
                self.id = row[0]
                self.avg_values = loads(row[1])
                self.count = row[2]
                self.start_time = row[3]
                self.end_time = row[4]
                self.count_sensor = loads(row[7])
            del actual_columns
            #del required_columns

        except:
            exception('Error creating History object')
         
    def __del__(self):
        try:
            self.connection.close()
        except:
            exception('Error deleting History object')
    
    def CalculateAverage(self, current_avg, new_value, count):
        return ((float(current_avg) * (count - 1)) + new_value) / count
    
    def CalculateSubItemAverages(self, avg_item, new_item, count):
        try:
            for key, value in new_item.items():
                try:
                    if key not in avg_item:
                        avg_item[key] = value
                    elif type(value) is dict:
                        avg_item[key] = self.CalculateSubItemAverages(avg_item[key], value, count)
                    else:
                        avg_item[key] = self.CalculateAverage(avg_item[key], value, count)
                except KeyError as e:
                    exception('Key not found')
        except:
            exception('Error calculating subitem averages')
        return avg_item
            
    def CalculateListAverages(self, avg_list, new_list, values_to_average, id_key, count):
        try:
            for item in new_list:               
                index = next((i for i, avg_item in enumerate(avg_list) if avg_item[id_key] == item[id_key]), None)
                if index is None:
                    avg_list.append(item)
                else:
                    for value in values_to_average:
                        if value in item:
                            avg_list[index][value] = self.CalculateAverage(avg_list[index][value], item[value], count)
        except:
            exception('Error calculating subitem averages')
        return avg_list
    
    def CalculateArrayAverage(self, avg_array, new_array, count):
        if len(avg_array) == 0:
            return new_array
        try:
            for key in avg_array:
                avg_array[key] = self.CalculateAverage(avg_array[key], new_array[key], count)
        except:
            exception('Error calculating array averages')
        return avg_array

    def CalculateNetworkSpeedAverages(self, current_avgs, new_sample, count):
        try:
            if 'NetworkSpeed' not in current_avgs:
                if 'NetworkSpeed' in new_sample:
                    current_avgs['NetworkSpeed'] = new_sample['NetworkSpeed']
                    return           
            if new_sample['NetworkSpeed'] != 'None':
                if current_avgs['NetworkSpeed'] == 'None':
                    current_avgs['NetworkSpeed'] = new_sample['NetworkSpeed']
                else:
                    current_avgs['NetworkSpeed'] = str(self.CalculateAverage(float(current_avgs['NetworkSpeed']), float(new_sample['NetworkSpeed']), count))
        except:
            exception('Error calculating network speed average')
                
    def CalculateSystemInfoAverages(self, current_avgs, new_sample, count):
        try:
            if 'SystemInfo' not in new_sample or new_sample['SystemInfo'] is None:
                return
            if 'SystemInfo' not in current_avgs:
                current_avgs['SystemInfo'] = new_sample['SystemInfo']
                return       
            #Calculate CPU averages
            try:
                if 'CpuLoad' not in current_avgs['SystemInfo']:
                    current_avgs['SystemInfo']['CpuLoad'] = new_sample['SystemInfo']['CpuLoad']
                else:        
                    current_avgs['SystemInfo']['CpuLoad'] = self.CalculateSubItemAverages(current_avgs['SystemInfo']['CpuLoad'], new_sample['SystemInfo']['CpuLoad'], count)
            except KeyError as e:
                debug('KeyError: {}'.format(e))
            except:    
                exception('Error calculating CPU load average')
            try:
                current_avgs['SystemInfo']['Cpu']['temperature'] = self.CalculateAverage(current_avgs['SystemInfo']['Cpu']['temperature'], new_sample['SystemInfo']['Cpu']['temperature'], count)
            except:
                exception('Error calculating CPU temperature average')
            #Calculate network averages
            try:
                for key in ('packets', 'bytes'):
                    for subkey in new_sample['SystemInfo']['Network'][key].keys():
                        current_avgs['SystemInfo']['Network'][key][subkey] = self.CalculateSubItemAverages(current_avgs['SystemInfo']['Network'][key][subkey], new_sample['SystemInfo']['Network'][key][subkey], count)
            except:
                # Ignore error if key doesn't exist
                pass
            #Calculate storage averages
            try:
                for subkey in new_sample['SystemInfo']['Storage']['throughput'].keys():
                    current_avgs['SystemInfo']['Storage']['throughput'][subkey] = self.CalculateSubItemAverages(current_avgs['SystemInfo']['Storage']['throughput'][subkey], new_sample['SystemInfo']['Storage']['throughput'][subkey], count)
            except:
                # Ignore error if one of the dicts doesn't contain 'throughput'
                pass
            current_avgs['SystemInfo']['Storage']['list'] = self.CalculateListAverages(current_avgs['SystemInfo']['Storage']['list'], new_sample['SystemInfo']['Storage']['list'], ('available', 'used', 'use'), 'mount', count)
            #Calculate memory averages
            current_avgs['SystemInfo']['Memory'] = self.CalculateSubItemAverages(current_avgs['SystemInfo']['Memory'], new_sample['SystemInfo']['Memory'], count)
            #Totals don't get averaged, they are just copied
            current_avgs['SystemInfo']['Memory']['total'] = new_sample['SystemInfo']['Memory']['total']
            current_avgs['SystemInfo']['Memory']['swap']['total'] = new_sample['SystemInfo']['Memory']['swap']['total']
        except:
            exception('Error calculating system info averages: current_avgs {}, new_sample {} '.format(current_avgs, new_sample))
        
    def CalculateSensorsInfoAverages(self, current_avgs, new_sample, count_sensor):
        try:
            logJson('History SensorsInfo average: '  + str(new_sample), 'history')
            info('Calculate sensor info averages: ' + str(count_sensor))
            if not new_sample:
                info('History average: New sample is empty.')
                return
            if 'SensorsInfo' in new_sample:
                #print('Calculating sensors list: ' + str(new_sample))
                #newSensorsDictionary = dict((i['sensor'], i) for i in data['SensorsInfo'])
                if 'SensorsInfo' not in current_avgs:
                    current_avgs['SensorsInfo'] = []
                    count_sensor['SensorsInfo'] = {}
                averageSensorsDictionary = {}
                if len(current_avgs['SensorsInfo']) > 0:
                    averageSensorsDictionary = dict((i['sensor'], i) for i in current_avgs['SensorsInfo'])
                if new_sample['SensorsInfo']:
                    for value in new_sample['SensorsInfo']:
                        if 'enabled' in value and value['enabled'] == 0:
                            continue
                        if value['sensor'] in averageSensorsDictionary:
                            #this means we need to calculate average
                            try:
                                if value['sensor'] not in count_sensor['SensorsInfo']:
                                    count_sensor['SensorsInfo'][value['sensor']] = 0
                                count_sensor['SensorsInfo'][value['sensor']] += 1
                                if value['type'] == 'Temperature':
                                    averageSensorsDictionary[value['sensor']]['Celsius'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['Celsius'], value['Celsius'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                    # averageSensorsDictionary[value['sensor']]['Fahrenheit'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['Fahrenheit'], value['Fahrenheit'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                    # averageSensorsDictionary[value['sensor']]['Kelvin'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['Kelvin'], value['Kelvin'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                if value['type'] == 'Pressure':
                                    averageSensorsDictionary[value['sensor']]['Pascal'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['Pascal'], value['Pascal'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                if value['type'] == 'Luminosity':
                                    averageSensorsDictionary[value['sensor']]['Lux'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['Lux'], value['Lux'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                if value['type'] == 'Distance':
                                    averageSensorsDictionary[value['sensor']]['Centimeter'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['Centimeter'], value['Centimeter'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                    averageSensorsDictionary[value['sensor']]['Inch'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['Inch'], value['Inch'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                ############################################################################################################
                                #averages for all fields that are arrays of values should not be done
                                # if value['type'] in ('ADC', 'DAC', 'PWM'):
                                #     #never do average for : channelCount, maxInteger, resolution
                                #     if value['type'] in ('ADC', 'DAC'):
                                #         averageSensorsDictionary[value['sensor']]['allInteger'] = self.CalculateArrayAverage(averageSensorsDictionary[value['sensor']]['allInteger'], value['allInteger'], count_sensor['SensorsInfo'][value['sensor']])
                                #         averageSensorsDictionary[value['sensor']]['allVolt'] = self.CalculateArrayAverage(averageSensorsDictionary[value['sensor']]['allVolt'], value['allVolt'], count_sensor['SensorsInfo'][value['sensor']])
                                #         averageSensorsDictionary[value['sensor']]['allFloat'] = self.CalculateArrayAverage(averageSensorsDictionary[value['sensor']]['allFloat'], value['allFloat'], count_sensor['SensorsInfo'][value['sensor']])
                                #     if value['type'] in ('PWM'):
                                #         averageSensorsDictionary[value['sensor']]['all'] = self.CalculateArrayAverage(averageSensorsDictionary[value['sensor']]['all'], value['all'], count_sensor['SensorsInfo'][value['sensor']])
                                # if value['type'] == 'GPIOPort':
                                #     #never do average for: channelCount
                                #     averageSensorsDictionary[value['sensor']]['all'] = self.CalculateArrayAverage(averageSensorsDictionary[value['sensor']]['all'], value['all'], count_sensor['SensorsInfo'][value['sensor']])
                                # if value['type'] == 'PiFaceDigital':
                                #     averageSensorsDictionary[value['sensor']]['all'] = self.CalculateArrayAverage(averageSensorsDictionary[value['sensor']]['all'], value['all'], count_sensor['SensorsInfo'][value['sensor']])
                                ############################################################################################################          
                                if value['type'] == 'Humidity':
                                    averageSensorsDictionary[value['sensor']]['float'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['float'], value['float'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                    averageSensorsDictionary[value['sensor']]['percent'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['percent'], value['percent'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                if value['type'] in ('DigitalSensor', 'DigitalActuator'):
                                    averageSensorsDictionary[value['sensor']]['value'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['value'], value['value'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                if value['type'] == 'AnalogSensor':
                                    averageSensorsDictionary[value['sensor']]['float'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['float'], value['float'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                    # averageSensorsDictionary[value['sensor']]['integer'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['integer'], value['integer'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                    # averageSensorsDictionary[value['sensor']]['volt'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['volt'], value['volt'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                if value['type'] == 'ServoMotor':
                                    averageSensorsDictionary[value['sensor']]['angle'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['angle'], value['angle'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                if value['type'] == 'AnalogActuator':
                                    averageSensorsDictionary[value['sensor']]['float'] = self.CalculateAverage(averageSensorsDictionary[value['sensor']]['float'], value['float'], count_sensor['SensorsInfo'][value['sensor']] ) 
                                #else:
                                #    current_avgs['SensorsInfo'].append(value)
                                #    count_sensor['SensorsInfo'][value['sensor']] = 1
                            except:
                                exception('Error calculating sensors info averages for: ' + str(value))
                        else:
                            current_avgs['SensorsInfo'].append(value)
                            count_sensor['SensorsInfo'][value['sensor']] = 1
        except:
            exception('Error calculating sensors info averages: current_avgs {}, new_sample {} '.format(current_avgs, new_sample))

    def CalculateAverages(self, current_avgs, new_sample, count, count_sensor):
        info('History CalculateAverages increment: ' + str(count))
        count += 1
        self.CalculateNetworkSpeedAverages(current_avgs, new_sample, count)
        self.CalculateSystemInfoAverages(current_avgs, new_sample, count)
        self.CalculateSensorsInfoAverages(current_avgs, new_sample, count_sensor)
        return count

    def SaveAverages(self, data):
        try:
            self.CheckRollover()
            self.count = self.CalculateAverages(self.avg_values, data, self.count, self.count_sensor)
            info('Save History Averages')
            self.end_time = time()
            if self.id is None:
                self.cursor.execute('INSERT INTO historical_averages VALUES (NULL,?,?,?,?,?,?,?)', (dumps(self.avg_values), self.count, self.start_time, self.end_time, History.RUNNING, History.NOT_READY, dumps(self.count_sensor)))
                self.connection.commit()
                self.id = self.cursor.lastrowid
            else:
                self.cursor.execute('REPLACE INTO historical_averages VALUES (?,?,?,?,?,?,?,?)', (self.id, dumps(self.avg_values), self.count, self.start_time, self.end_time, History.RUNNING, History.NOT_READY, dumps(self.count_sensor)))
                self.connection.commit()
        except:
            exception('SaveAverages Update database exception')
        #info(self.avg_values)
        
    def SaveIntervalAverage(self, interval, start, end):
        sub_interval = self.GetSubInterval(interval)
        startTimestamp = (start - datetime(1970, 1, 1)).total_seconds()
        endTimestamp = (end - datetime(1970, 1, 1)).total_seconds()
        self.cursor.execute('SELECT data, start, end FROM historical_averages WHERE interval = ? AND start >= ? AND end <= ?', (sub_interval, startTimestamp, endTimestamp))
        results = self.cursor.fetchall()
        avg = {}
        count = 0
        count_sensor = {}
        count_sensor['SensorsInfo'] = {}
        for row in results:            
            count = self.CalculateAverages(avg, loads(row[0]), count, count_sensor)
        if avg:
            start_time = min(results, key=itemgetter(1))[1]
            end_time = max(results, key=itemgetter(2))[2]
            self.cursor.execute('INSERT INTO historical_averages VALUES (NULL,?,?,?,?,?,?,?)', (dumps(avg), count, start_time, end_time, interval, History.READY, dumps(count_sensor)))
            self.connection.commit()
            
    def GetIntervalAverage(self, interval):
        avg = {}
        self.cursor.execute('SELECT id, data, start, end FROM historical_averages WHERE interval = ? AND send = ? ORDER BY end ASC LIMIT 1', (interval, History.READY))
        results = self.cursor.fetchall()
        for row in results:
            avg = loads(row[1])
            avg['StartTime'] = row[2]
            avg['EndTime'] = row[3]
            interval_types = {History.HOUR: 1, History.DAY: 2, History.WEEK: 3, History.MONTH: 4, History.YEAR: 5}
            avg['Type'] = interval_types[interval]
            self.cursor.execute('UPDATE historical_averages SET send = ? WHERE id = ?', (History.SENDING, row[0]))
            self.connection.commit()
        return avg      

    def GetHistoricalData(self):
        data = []
        try:
            if(any(item in argv for item in ['-t', '--test'])):
                #In debug mode use test data if it is available
                with open('/etc/myDevices/history_test.json', encoding='utf-8') as data_file:
                    data = loads(data_file.read())
                if data:
                    rename('/etc/myDevices/history_test.json', '/etc/myDevices/history_test.json.sent')
                    return data
        except:
            pass
        if self.DataReady():
            try:
                for interval in (History.HOUR, History.DAY, History.WEEK, History.MONTH, History.YEAR):
                    avg = self.GetIntervalAverage(interval)
                    if avg:
                        data.append(avg)
                        return data
            except:
                exception('Error getting historical data')
        return data

    def DataReady(self):
        try:
            #If we are currently sending any data, don't send any new data until that send is finished
            self.cursor.execute('SELECT COUNT(*) FROM historical_averages WHERE send = ?', (History.SENDING,))
            count = self.cursor.fetchone()
            if count[0] > 0:
                return False
            self.cursor.execute('SELECT COUNT(*) FROM historical_averages WHERE send = ?', (History.READY,))
            count = self.cursor.fetchone()
            return count[0] > 0
        except:
            pass
        return False
        
    def Reset(self):
        self.cursor.execute('UPDATE historical_averages SET send = ? WHERE send = ?', (History.READY, History.SENDING))
        self.connection.commit()
 
    def Sent(self, success, history_data):
        info(('Sent History data with {}.').format(success))
        for item in history_data:
            if success:
                self.cursor.execute('UPDATE historical_averages SET send = ? WHERE send = ? AND start = ? AND end = ?', (History.SENT, History.SENDING, item['StartTime'], item['EndTime']))
            else:
                self.cursor.execute('UPDATE historical_averages SET send = ? WHERE send = ? AND start = ? AND end = ?', (History.READY, History.SENDING, item['StartTime'], item['EndTime']))
        self.connection.commit()
        self.DeleteSentData()
    
    def DeleteSentData(self):
        info('Deleting sent data...')
        for interval in (History.DAY, History.WEEK, History.MONTH, History.YEAR):
            self.DeleteSubIntervalData(interval)
    
    def DeleteSubIntervalData(self, interval):
        try:
            sub_interval = self.GetSubInterval(interval)
            self.cursor.execute('SELECT start, end FROM historical_averages WHERE interval = ?', (interval,))
            results = self.cursor.fetchall()
            for row in results:
                self.cursor.execute('DELETE FROM historical_averages WHERE interval = ? AND start >= ? AND end <= ? AND send = ?', (sub_interval, row[0], row[1], History.SENT))
                self.connection.commit()
        except:
            exception('Error deleting sent data')
            
    def GetSubInterval(self, interval):
        try:
            intervals = (History.HOUR, History.DAY, History.WEEK, History.MONTH, History.YEAR)
            index = intervals.index(interval)
            if index != 0:
                return(intervals[index - 1])
        except:
            pass
        return None    
    
    def CheckRollover(self):
        rolled_over = False
        if self.end_time is None:
            return rolled_over
        #Check if the hour has changed
        current_time = time()
        current_hour = datetime.utcfromtimestamp(current_time).replace(minute=0, second=0, microsecond=0)
        last_saved_hour = datetime.utcfromtimestamp(self.end_time).replace(minute=0, second=0, microsecond=0)
        if current_hour != last_saved_hour:
            rolled_over = True
            last_saved_hour_end = last_saved_hour + timedelta(hours=1)
            timestamp = (last_saved_hour_end - datetime(1970, 1, 1)).total_seconds()
            self.cursor.execute('UPDATE historical_averages SET end = ?, interval = ?, send = ? WHERE id = ?', (timestamp, History.HOUR, History.READY, self.id))
            self.connection.commit()
            self.id = None
            self.avg_values = {}
            self.count = 0
            self.start_time = time()
        #Check if the day has changed
        current_day = current_hour.replace(hour=0)
        last_saved_day = last_saved_hour.replace(hour=0)
        if current_day != last_saved_day:
            day_end = last_saved_day + timedelta(days=1)
            self.SaveIntervalAverage(History.DAY, last_saved_day, day_end)  
        #Check if the week has changed
        current_week = current_day - timedelta(days=current_day.weekday())
        last_saved_week = last_saved_day - timedelta(days=last_saved_day.weekday())
        if current_week != last_saved_week:
            week_end = last_saved_week + timedelta(weeks=1)
            self.SaveIntervalAverage(History.WEEK, last_saved_week, week_end)
        #Check if the month has changed
        current_month = current_day.replace(day=1)
        last_saved_month = last_saved_day.replace(day=1)
        if current_month != last_saved_month:
            next_month = last_saved_month + timedelta(days=32)
            month_end = next_month.replace(day=1)
            self.SaveIntervalAverage(History.MONTH, last_saved_month, month_end)
        #Check if the year has changed
        current_year = current_month.replace(day=1)
        last_saved_year = last_saved_month.replace(day=1)
        if current_year != last_saved_year:
            year_end = last_saved_year.replace(year=last_saved_year.year + 1)
            self.SaveIntervalAverage(History.YEAR, last_saved_year, year_end)
        return rolled_over