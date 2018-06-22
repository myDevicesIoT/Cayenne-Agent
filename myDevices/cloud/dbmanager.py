from sqlite3 import connect
from myDevices.utils.logger import exception, info, warn, error, debug, setDebug
from threading import RLock
from time import sleep
from myDevices.utils.singleton import Singleton

connection = None
cursor = None
mutex = RLock()

class DbManager(Singleton):
    def CreateTable(tablename, columns, required_columns = None):
        try:
            with mutex:
                if not cursor or not connection:
                    return False
                if required_columns and len(required_columns):
                    cursor.execute('PRAGMA table_info(' +  tablename + ')')
                    actual_columns = [column[1] for column in cursor.fetchall()]
                    if actual_columns != required_columns:
                        try:
                            if actual_columns:
                                warn(tablename + ' table columns {} do not match required columns {}, dropping table'.format(actual_columns, required_columns) + " From: " + str(hex(id(connection))) + " " + str(hex(id(cursor)))  )
                            cursor.execute('DROP TABLE ' + tablename)
                            connection.commit()
                        except:
                            pass
                    del actual_columns
                cursor.execute('CREATE TABLE IF NOT EXISTS ' + tablename + ' ('+ str(columns) +')')
                connection.commit()
                # sleep(5)
        except Exception as ex:
            error("Failed to CreateTable: " + tablename + " " + str(ex))
            return False
        return True
    def Insert(tablename, *values):
        if not cursor or not connection:
            return
        with mutex:
            statement = 'INSERT INTO ' + tablename + ' VALUES '
            if len(values) == 1:
                statement = statement + '(\'' + str(values[0]) + '\')'
            else:
                statement = statement + str(values)
            #print(statement)
            cursor.execute(statement)
            connection.commit()
            return cursor.lastrowid
    def Update(tablename, setClause, setValue, whereClause, whereValue):
        if not cursor or not connection:
            return False
        with mutex:
            try:
                statement = 'UPDATE ' + tablename + ' SET ' + setClause + ' WHERE ' + whereClause
                cursor.execute(statement, (setValue, whereValue))
                connection.commit()
            except Exception as ex:
                exception('DbManager::Update except ' + str(ex))
                return False
            return True
    def Replace(tablename, *values):
        #Replace data in column. The first parameter in values must specify the id of the column to replace.
        if not cursor or not connection:
            return False
        with mutex:
            statement = 'REPLACE INTO ' + tablename + ' VALUES ' + str(values)
            cursor.execute(statement)
            connection.commit()
            return True
    def Delete(tablename, id):
        if not cursor or not connection:
            return False
        with mutex:
            statement = 'DELETE FROM ' + tablename + ' WHERE id = ?'
            cursor.execute(statement, (id,))
            connection.commit()
            return True
    def Select(tablename, where = ''):
        if not cursor or not connection:
            return
        with mutex:
            cursor.execute("select * from " + tablename + where)
            return cursor.fetchall()
    def DeleteAll(tablename):
        if not cursor or not connection:
            return False
        with mutex:
            statement = 'DELETE FROM ' + tablename
            cursor.execute(statement)
            connection.commit()
            return True
  
def test():
    tablename = 'test_sensors'
    DbManager.CreateTable(tablename, "id TEXT PRIMARY KEY", ['id'])
    idtest = "XXXXXXXR"
    rowId = DbManager.Insert(tablename, idtest)
    print('RowID: ' + str(rowId))
    #DbManager.Update(tablename, "XXXXX2", rowId)
    results = DbManager.Select(tablename)
    print ('Results: ')
    if results:
        for row in results:
            print (str(row))
        DbManager.Delete(tablename, idtest)
        results = DbManager.Select(tablename)
        print ('Results: ' + str(results))

#Initialize the database
try:
    connection = connect('/etc/myDevices/agent.db', check_same_thread = False)
    cursor = connection.cursor()
except Exception as ex:
    error('DbManager failed to initialize: ' + str(ex))
# DbManager.CreateTable('scheduled_items', "id TEXT PRIMARY KEY, data TEXT", ['id', 'data'])
DbManager.CreateTable('disabled_sensors', "id TEXT PRIMARY KEY", ['id'])
DbManager.CreateTable('historical_averages', "id INTEGER PRIMARY KEY, data TEXT, count INTEGER, start TIMESTAMP, end TIMESTAMP, interval TEXT, send TEXT, count_sensor TEXT", ['id', 'data', 'count', 'start', 'end', 'interval', 'send', 'count_sensor'])
