import paho.mqtt.client as mqtt
import subprocess
import time
from datetime import date, datetime
import threading
import ephem
import tweepy
from ConfigParser import SafeConfigParser
import logging
import logging.handlers

# Constant
PREFIX = "wx/EI7IG-1"
exit_me = False

parser = SafeConfigParser()
parser.read('config.ini')

my_name = parser.get('mqtt', 'clientname')
output_format = my_name+' %(message)s'

# Set up Logger object
logger = logging.getLogger(my_name)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s '+output_format)

# Set up a handler for pushing to syslog
# This line should be used for a properly listening syslogd
#handler = logging.handlers.SysLogHandler(facility=logging.handlers.SysLogHandler.LOG_DAEMON, address=('localhost', 514))
handler = logging.handlers.SysLogHandler(facility=logging.handlers.SysLogHandler.LOG_DAEMON, address='/dev/log')
# Change to our format
formatter = logging.Formatter(output_format)
handler.setFormatter(formatter)
logger.addHandler(handler)


# MyClass
class ShackData(threading.Thread):
    def __init__(self):
        self.log_level = parser.get('logging', 'level')
        self.warning_text = ''
        self.wind_text = ''
        self.wind_direction = 0
        self.wind_speed = 0  # Meters Per Second
        self.wind_warning = 0
        self.wind_gust = 0
        self.max_wind_gust = 0
        self.wind_gust_warning = 0
        self.wind_cardinal = ''
        self.temperature = 0
        self.max_temperature = 0
        self.min_temperature = 0
        self.temp_warning = 0
        self.rain_1h = 0
        self.rain_1h_warning = 0
        self.rain_24h = 0
        self.rain_24h_warning = 0
        self.humidity = 0
        self.max_humidity = 0
        self.min_humidity = 0
        self.pressure = 0
        self.max_pressure = 0
        self.min_pressure = 0
        # This should never be seen
        self.pressure_direction = ''
        self.pv_watts = 0
        self.pv_samples = 0
        self.pv_average = 0
        self.pv_total = 0
        self.pv_dropped = True
        self.pv_volts = 0
        self.sun = False
        self.sun_state = 0  # No Sun (starting state)
        self.today = date.today()
        self.next_rising = 0
        self.next_setting = 0
        self.timestamp = datetime.now()
        self.quit = False
        self.lock = threading.Lock()
        threading.Thread.__init__(self)
        self.get_sunset_sunrise()
        #self.check_sun_up()
        self.api = ''
        self.tweet = parser.getboolean('twitter', 'tweet')

    def run(self):
        global exit_me
        logger.info("Fred starting ...")

        # Loop until told otherwise
        while (not exit_me):
            # Check here.
            self.reset_max_min()

            now = datetime.now()
            # Is it time to send a WX update?
            if self.ok_send_wx(now):
                self.send_wx_message(now)

            # Is it time to send a telemetry update?
            if self.ok_send_telemetry(now):
                self.send_telemetry_message(now)

            #  wait one second before trying again.
            time.sleep(1.0)

    def send_wx_message(self, now):
        # Make sure there are sensible temparture and max and min values before displaying anything
        if(self.min_temperature != self.max_temperature):
            status1 = "%02.0f:%02.0f Temp %2.1fC (%2.1f, %2.1f) " % (now.hour, now.minute, self.temperature, self.min_temperature, self.max_temperature)
        else:
            status1 = "%02.0f:%02.0f Temp %2.1fC " % (now.hour, now.minute, self.temperature)

        status2 = "Hum. %2.0f%% Rain %2.1f mm (1h) %2.1f mm (24h) Wind %02.1f km/h %s %s%4.1f hPa%s%s" % (self.humidity, float(self.rain_1h), float(self.rain_24h), float(self.wind_speed)*3.6, self.wind_cardinal, self.wind_text, self.pressure, self.pressure_direction, self.warning_text)

        # Can't get here unless min_temperature != 0
        if self.ok_send_rising(now):
            status = status1+status2+" Sunrise %02.0f:%02.0f" % (self.next_rising.hour, self.next_rising.minute)
        elif self.ok_send_setting(now):
            status = status1+status2+" Sunset %02.0f:%02.0f" % (self.next_setting.hour, self.next_setting.minute)
        else:
            status = status1+status2

        self.send_tweet(status)
        notify("Weather Update", status)
        logger.debug(status)

    def send_telemetry_message(self, now):
        status = "PV output is %02.0f Watts (%02.1f)%% (Avg. %02.0f)" % (float(self.pv_watts), float(self.pv_watts)/540*100, float(self.pv_average))
        self.send_tweet(status)
        notify("Telemetry", status)
        logger.debug(status)

    def send_tweet(self, msg):
        if self.tweet is True:
            logger.debug("Sending tweet")
            try:
                self.api.update_status(msg)
            except Exception:
                logger.info("Caught tweety exception")
                pass
        else:
            logger.debug("self.tweet is False")

    def ok_send_setting(self, now):
        if(now < self.next_setting and
           now.date() == self.next_setting.date()):
            return True
        else:
            return False

    def ok_send_rising(self, now):
        if(now < self.next_rising and
           now.date() == self.next_rising.date()):
            return True
        else:
            return False

    # Niave method
    def get_wx_interval(self):
        level = self.get_wx_warning_level()
        if level == 0:
            return 120
        elif level == 1:
            return 60
        elif level == 2:
            return 30
        elif level == 3:
            return 15

    def get_wx_warning_level(self):
        if(self.wind_warning == 1 or
           self.wind_gust_warning == 1 or
           self.temp_warning == 1 or
           self.rain_1h_warning == 1 or
           self.rain_24h_warning == 1):
            self.warning_text = " Yellow Alert"
            return 1
        elif(self.wind_warning == 2 or
             self.wind_gust_warning == 2 or
             self.temp_warning == 2 or
             self.rain_1h_warning == 2 or
             self.rain_24h_warning == 2):
            self.warning_text = " Orange Alert"
            return 2
        elif(self.wind_warning == 3 or
             self.wind_gust_warning == 3 or
             self.temp_warning == 3 or
             self.rain_1h_warning == 3 or
             self.rain_24h_warning == 3):
            self.warning_text = " Red Alert"
            return 3
        else:
            self.warning_text = ""
            return 0

    def ok_send_wx(self, now):
        interval = self.get_wx_interval()
        if self.min_temperature != self.max_temperature and now.second == 15:
            # 120 minute intervals, even hour, 15 seconds past the 0 minute
            if(interval == 120 and
               now.hour % 2 == 0 and
               now.minute == 0):
                return True
            # 60 minute interval, every hour, 15 second past the 0 minute
            elif interval == 60 and now.minute == 0:
                return True
            # every 30 minutes, 15 seconds past the minute
            elif interval == 30 and now.minute % 30 == 0:
                return True
            # every 15 minutes, 15 seconds past the minute
            elif interval == 15 and now.minute % 15 == 0:
                return True
            else:
                return False

    def ok_send_telemetry(self, now):
        if(self.check_sun_up(now) and
           now.hour % 2 == 0 and
           now.minute == 45 and
           now.second == 20):
            return True
        else:
            return False

    def check_interval(self, value):
        now = datetime.now()
        difference = now - self.time_stamp()
        if difference.total_seconds() >= value:
            return True
        else:
            return False

    def get_sunset_sunrise(self):
        o = ephem.Observer()
        o.lat = parser.get('gps', 'lat')
        o.long = parser.get('gps', 'long')
        s = ephem.Sun()
        s.compute()
        self.next_rising = ephem.localtime(o.next_rising(s))
        self.next_setting = ephem.localtime(o.next_setting(s))

    def set_wind_speed(self, value):
        with self.lock:
            self.wind_speed = float(value)
            if float(value) < 12.0 / 3.6:
                self.wind_text = " "
            elif float(value) < 20 / 3.6:
                self.wind_text = "Gentle Breeze "
            elif float(value) < 29 / 3.6:
                self.wind_text = "Moderate Breeze "
            elif float(value) < 38 / 3.6:
                self.wind_text = "Fresh Breeze "
            elif float(value) < 50 / 3.6:
                self.wind_text = "Strong Breeze "
            elif float(value) < 62 / 3.6:
                self.wind_text = "Near Gale "
            elif float(value) < 75 / 3.6:
                self.wind_text = "Gale "
            elif float(value) < 89 / 3.6:
                self.wind_text = "Strong Gale "
            elif float(value) < 103 / 3.6:
                self.wind_text = "Storm "
            elif float(value) < 118 / 3.6:
                self.wind_text = "Violent Storm "
            elif float(value) >= 118 / 3.6:
                self.wind_text = "Hurricane Force "
            # Warnings and update interval
            if float(value) < 50 / 3.6:
                self.wind_warning = 0
            elif float(value) < 65 / 3.6:
                self.wind_warning = 1
            elif float(value) < 80 / 3.6:
                self.wind_warning = 2
            elif float(value) >= 80 / 3.6:
                self.wind_warning = 3
            #if self.wind_warning > 0:
            #    logger.debug("wind warning level is: %d" % self.wind_warning)

    def set_wind_gust(self, value):
        with self.lock:
            self.wind_gust = float(value)
            # If the value is greater than existing or 0 or  new day.
            if value > self.max_wind_gust:
                self.max_wind_gust = value
            # Warnings and update interval
            if float(value) < 90 / 3.6:
                self.wind_gust_warning = 0
            elif float(value) < 110 / 3.6:
                self.wind_gust_warning = 1
            elif float(value) < 130 / 3.6:
                self.wind_gust_warning = 2
            elif float(value) >= 130 / 3.6:
                self.wind_gust_warning = 3
            #if self.wind_gust_warning > 0:
            #    logger.debug("wind_gust warning level is: %d" % self.wind_gust_warning)

    def set_wind_direction(self, value):
        with self.lock:
            self.wind_direction = int(value)
        # see https://en.wikipedia.org/wiki/Points_of_the_compass#Compass_point_names
        if 5.63 <= int(value) <= 16.87:
            self.set_wind_cardinal("NbE")
        elif 16.88 <= int(value) <= 28.12:
            self.set_wind_cardinal("NNE")
        elif 28.13 <= int(value) <= 39.37:
            self.set_wind_cardinal("NEbN")
        elif 39.38 <= int(value) <= 50.62:
            self.set_wind_cardinal("NE")
        elif 50.63 <= int(value) <= 61.87:
            self.set_wind_cardinal("NEbE")
        elif 61.88 <= int(value) <= 73.12:
            self.set_wind_cardinal("ENE")
        elif 73.13 <= int(value) <= 84.37:
            self.set_wind_cardinal("EbN")
        elif 84.38 <= int(value) <= 95.62:
            self.set_wind_cardinal("E")
        elif 95.63 <= int(value) <= 106.87:
            self.set_wind_cardinal("EbS")
        elif 106.88 <= int(value) <= 118.12:
            self.set_wind_cardinal("ESE")
        elif 118.13 <= int(value) <= 129.37:
            self.set_wind_cardinal("SEbE")
        elif 129.38 <= int(value) <= 140.62:
            self.set_wind_cardinal("SE")
        elif 140.63 <= int(value) <= 151.87:
            self.set_wind_cardinal("SEbS")
        elif 151.88 <= int(value) <= 163.12:
            self.set_wind_cardinal("SSE")
        elif 163.13 <= int(value) <= 174.37:
            self.set_wind_cardinal("SbE")
        elif 174.38 <= int(value) <= 185.62:
            self.set_wind_cardinal("S")
        elif 185.63 <= int(value) <= 196.87:
            self.set_wind_cardinal("SbW")
        elif 196.88 <= int(value) <= 208.12:
            self.set_wind_cardinal("SSW")
        elif 208.13 <= int(value) <= 219.37:
            self.set_wind_cardinal("SWbS")
        elif 219.38 <= int(value) <= 230.62:
            self.set_wind_cardinal("SW")
        elif 230.63 <= int(value) <= 241.87:
            self.set_wind_cardinal("SWbW")
        elif 241.88 <= int(value) <= 253.12:
            self.set_wind_cardinal("WSW")
        elif 253.13 <= int(value) <= 264.37:
            self.set_wind_cardinal("WbS")
        elif 264.38 <= int(value) <= 275.62:
            self.set_wind_cardinal("W")
        elif 275.63 <= int(value) <= 286.87:
            self.set_wind_cardinal("WbN")
        elif 286.88 <= int(value) <= 298.12:
            self.set_wind_cardinal("WNW")
        elif 298.13 <= int(value) <= 309.37:
            self.set_wind_cardinal("NWbW")
        elif 309.38 <= int(value) <= 320.62:
            self.set_wind_cardinal("NW")
        elif 320.63 <= int(value) <= 331.87:
            self.set_wind_cardinal("NWbN")
        elif 331.88 <= int(value) <= 343.12:
            self.set_wind_cardinal("NNW")
        elif 343.13 <= int(value) <= 354.37:
            self.set_wind_cardinal("NbW")
        elif 354.38 <= int(value) <= 360 or 0 <= int(value) <= 5.62:
            self.set_wind_cardinal("N")
        else:
            raise ValueError("Value was < 0 or > 360")

    def set_wind_cardinal(self, value):
        with self.lock:
            self.wind_cardinal = value

    def set_temperature(self, value):
        with self.lock:
            self.temperature = float(value)
            if(self.min_temperature > float(value) or
               self.min_temperature == 0):
                self.min_temperature = float(value)

            if self.max_temperature < float(value):
                self.max_temperature = float(value)

            # Warnings and update interval
            if(self.min_temperature < -9 or
               self.max_temperature < -1 or
               self.max_temperature > 30):
                self.temp_warning = 3
            elif(self.min_temperature < -5 and
                 self.max_temperature < 0 or
                 self.min_temperature > 20):
                self.temp_warning = 2
            elif(self.min_temperature == -3 or
                 self.min_temperature == -4 and
                 self.max_temperature < 2
                 ):
                self.temp_warning = 1
            else:
                self.temp_warning = 0
            #if self.temp_warning > 0:
            #    logger.debug("temp warning level is: %d" % self.temp_warning)

    def set_rain_1h(self, value):
        with self.lock:
            self.rain_1h = float(value)
            # Warnings and update interval
            # > 20mm in 6h is 3.33mm in 1h
            if self.rain_1h > 3.33:
                self.rain_1h_warning = 1
            # > 30mm in 6h is 5mm in 1h
            elif self.rain_1h > 5:
                self.rain_1h_warning = 2
            # > 40mm in 6h is 6.66mm in 1h
            elif self.rain_1h > 6.66:
                self.rain_1h_warning = 3
            # < 20mm in 6h
            else:
                self.rain_1h_warning = 0
            #if self.rain_1h_warning > 0:
            #    logger.debug("rain_1h warning level is: %d" % self.rain_1h_warning)

    def set_rain_24h(self, value):
        with self.lock:
            self.rain_24h = float(value)
            # Warnings and update interval
            # > 30mm in 24h
            if self.rain_24h > 30:
                self.rain_24h_warning = 1
            # > 50mm in 24h
            elif self.rain_24h > 50:
                self.rain_24h_warning = 2
            # > 70mm in 24h
            elif self.rain_24h > 70:
                self.rain_24h_warning = 3
            # < 30mm in 24h
            else:
                self.rain_24h_warning = 0

            #if self.rain_24h_warning > 0:
            #    logger.debug("rain_24h warning level is: %d" % self.rain_24h_warning)

    def set_humidity(self, value):
        with self.lock:
            self.humidity = int(value)
            if self.min_humidity > int(value) or self.min_humidity == 0:
                self.min_humidity = int(value)

            if self.max_humidity < int(value):
                self.max_humidity = int(value)

    def set_pressure(self, value):
        with self.lock:
            if self.pressure != 0:
                if float(value) > self.pressure + 0.2:
                    self.pressure_direction = ' and rising '
                elif float(value) < self.pressure - 0.2:
                    self.pressure_direction = ' and falling '
                else:
                    self.pressure_direction = ' '

            self.pressure = float(value)
            if self.min_pressure > float(value) or self.min_pressure == 0:
                self.min_pressure = float(value)

            if self.max_pressure < float(value):
                self.max_pressure = float(value)

    def set_pv_watts(self, value):
        # Values < 0 not possible
        if self.is_sun_up():
            self.pv_watts = int(value)
            self.pv_samples = int(self.pv_samples + 1)
            self.pv_total = int(self.pv_total) + int(value)
            self.pv_average = float(self.pv_total / self.pv_samples)

    def set_battery_volts(self, value):
        # Values < 0 not possible
        self.battery_volts = float(value)

    def check_sun_up(self, now):
        if self.next_rising <= now <= self.next_setting:
            with self.lock:
                self.sun = True
            return True
        else:
            return False

    def sun_up(self):
        self.sun = True

    def is_sun_up(self):
        return self.sun

    def time_stamp(self):
        with self.lock:
            return self.timestamp

    def set_time_stamp(self, value):
        with self.lock:
            self.timestamp = value

    def reset_max_min(self):
        if self.today != date.today():
            logger.info("Resetting max/min")
            with self.lock:
                self.wind_speed = 0
                self.wind_gust = 0
                self.max_wind_gust = 0
                self.max_temperature = 0
                self.min_temperature = 0
                self.max_humidity = 0
                self.min_humidity = 0
                self.max_pressure = 0
                self.min_pressure = 0
                self.pv_samples = 0
                self.pv_total = 0
                self.pv_average = 0
                self.rain_24h = 0
                self.today = date.today()
                self.get_sunset_sunrise()
                return True
        else:
            return False

    def process_pv_messages(self, payload):
        now = datetime.now()
        myMsg = ""
        # Have We PV output?
        # Sun up. Should be after dawn and panels start production
        if(int(payload) > 0 and
           self.check_sun_up(now) and
           self.sun_state != 3):
            myMsg = "The Sky's Awake so I'm Awake"
            state = 1
        # If the sun is already up, then a we had some cloud cover
        elif(int(payload) > 0 and self.is_sun_up()):
            myMsg = "Welcome back Mr. Sun."
            state = 2
        # Sun is already up but has dissappeared but also we can be past
        # sunrise before payload > 0
        elif(int(payload) == 0 and self.is_sun_up() and self.sun_state == 1 or self.sun_state == 2):
            myMsg = "Woops, where did the Sun go?"
            state = 3
        # Sun has gone and past sunset
        elif(int(payload) == 0 and not self.check_sun_up(now) and self.sun_state == 1 or self.sun_state == 2):
            myMsg = "Bye Bye Mr. Sun, see you tomorrow"
            state = 4
        else:
            myMsg = "Setting Sun 'state' to 0"
            state = 0
        self.set_pv_watts(payload)

        if myMsg != "" and self.sun_state != state:
            logger.debug(" self.sun_state %d, state %d" % (self.sun_state, state ))
            self.sun_state = state
            notify("PV Update", myMsg)
            logger.debug(myMsg)

    # Serial to parallel convertor
    def process_wx_messages(self, topic, payload):
        myMsg = ""
        if topic == PREFIX+"/wind_direction":
            self.set_wind_direction(payload)
        elif topic == PREFIX+"/wind_speed":
            self.set_wind_speed(payload)
            myMsg = "Wind speed is {:3.2f} km/h ({:3.2f})".format(float(payload) * 3.6,
                                                                      float(self.wind_speed) * 3.6)
        #
        elif topic == PREFIX+"/wind_gust":
            if self.wind_gust >= self.max_wind_gust:
                self.set_wind_gust(payload)
                myMsg = "Wind gust is {:3.2f} km/h ({:3.2f})".format(float(payload) * 3.6, float(self.wind_gust) * 3.6)
            else:
                logger.debug("Wind gust has not changed")
        #
        elif topic == PREFIX+"/temperature":
            self.set_temperature(payload)
            myMsg = "Temperature is "+payload+" Deg.C"
        #
        elif topic == PREFIX+"/rain_1h":
            if self.rain_1h != payload:
                myMsg = "Rain for last hour is "+payload+" mm"
                self.set_rain_1h(payload)
            else:
                logger.debug("No Rain in last hour")
        #
        elif topic == PREFIX+"/rain_24h":
            if self.rain_24h != payload:
                myMsg = "Rain for last 24hours is "+payload+" mm"
                self.set_rain_24h(payload)
            else:
                logger.debug("No Rain in last 24 hours")
        #
        elif topic == PREFIX+"/humidity":
            self.set_humidity(payload)
            if self.max_humidity != self.min_humidity:
                myMsg = "Humidity is "+payload+"% ("+str(self.min_humidity)+","+str(self.max_humidity)+")"
            else:
                myMsg = "Humidity is "+payload
        #
        elif topic == PREFIX+"/pressure":
            # Always set to keep 'rising/falling' up-to-date
            self.set_pressure(payload)
            if self.pressure != float(payload):
                myMsg = "Pressure is "+payload+" hPa ("+str(self.min_pressure)+","+str(self.max_pressure)+")"+" "+self.pressure_direction
            else:
                myMsg = "Pressure is "+payload+" hPa "
        else:
            logger.debug("Unknown Weather Value %s:%s" % (topic, payload))
        # If the parameter hasn't changed, then myMsg will be blank.
        if myMsg != "":
            notify("Weather Update", myMsg)
            logger.info(myMsg)

    def process_sat_messages(self, payload):
        # Only send after dark
        if("ISS" in payload and
           "visible" in payload):  # and Visible in payload:
            self.send_tweet(payload)
            logger.info(payload)
        else:
            logger.info(payload)

    def process_battery_messages(self, payload):
        self.set_battery_volts(payload)


# Send desktop notification.
def notify(title, message):
    sendmessage(title, message)


# Send Desktop notification
def sendmessage(title, message):
    subprocess.Popen(['notify-send', str(title), str(message), '-t', '10000'])


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logger.debug("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe([("house/debug", 0),
                      ("wx/EI7IG-1/#", 0),
                      ("house/office/sat/#", 0),
                      ("house/office/radio/#", 0),
                      ("house/energy/owl/pv", 0),
                      ("house/energy/battery/voltage/#", 0)])
#   client.subscribe(parser.get('mqtt', 'topics'))
    logger.info("Subscribed")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, MyShack, msg):
    global exit_me
    # Output from the cc128 perl scripts
    if msg.topic == "house/energy/owl/pv":
        MyShack.process_pv_messages(msg.payload)
    elif msg.topic == "house/energy/battery/voltage":
        MyShack.process_battery_messages(msg.payload)
    # Radio has changed state
    elif msg.topic == "house/office/radio/ft847":
        print (msg.topic+" "+msg.payload)
        sendmessage(msg.topic, msg.payload)
    # Control Messages
    elif msg.topic == "house/debug":
        #
        if msg.payload.upper() == "DEBUG":
            logger.info("Logging level now {}".format(msg.payload.upper()))
            logger.setLevel(logging.DEBUG)
        #
        if msg.payload.upper() == "INFO":
            logger.info("Logging level now {}".format(msg.payload.upper()))
            logger.setLevel(logging.INFO)
        #
        if msg.payload.upper() == "EXIT":
            logger.info("Received exit so exiting...")
            exit_me = True
            client.disconnect()
        if msg.payload.upper() == "REDALERT":
            logger.info("Setting RedAlert")
            MyShack.wind_gust_warning = 3

    # Ok, if its not any of the above, it must be weather data
    # ISS is nearby
    elif "sat" in msg.topic:
        MyShack.process_sat_messages(msg.payload)
    else:
        MyShack.process_wx_messages(msg.topic, msg.payload)


def main():
    MyShack = ShackData()
    if MyShack.tweet is True:
        logger.debug("Initialising twitter object")
        auth = tweepy.OAuthHandler(parser.get('twitter', 'consumer_key'),
                                   parser.get('twitter', 'consumer_secret'))

        auth.set_access_token(parser.get('twitter', 'access_key'),
                              parser.get('twitter', 'access_secret'))
        MyShack.api = tweepy.API(auth)

    MyShack.start()

    client = mqtt.Client(parser.get('mqtt', 'clientname'),
                         userdata=MyShack,
                         clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(parser.get('mqtt', 'server'),
                   parser.get('mqtt', 'port'), 60)

    # Loop forever
    try:
        client.loop_forever()
    # Catches SigINT
    except KeyboardInterrupt:
        global exit_me
        exit_me = True
        client.disconnect()
        logger.info("Exiting main thread")
        time.sleep(2.0)

if __name__ == '__main__':
    main()