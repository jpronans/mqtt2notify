import unittest2 as unittest
import mqtt2notify
import time
from datetime import date, datetime, timedelta
import ephem
import mox


class mqtt2notifyTest(unittest.TestCase):
    def setUp(self):
        self.shack = mqtt2notify.ShackData()
        self.timestamp = self.shack.time_stamp()
#    def tearDown(self):
#        self.mox.UnsetStubs()

    # Has the time interval elapsed
    def test_check_interval(self):
        # Should be false
        self.assertFalse(self.shack.check_interval(60))
        # Time difference is now 1 hour
        now = datetime.now()
        one_hour = timedelta(hours=1)
        # Set tome to 1 hour in the past
        self.shack.set_time_stamp(now - one_hour)
        # We know we have moved one hour so this should be true
        # We have moved more than 3500 seconds
        self.assertTrue(self.shack.check_interval(3500))
        # This should be false.
        # We have not moved more than 3700 seconds
        self.assertFalse(self.shack.check_interval(3700))

    def test_wind_speed_zero(self):
        self.shack.set_wind_speed(0)
        self.assertEqual(self.shack.wind_speed, 0)

    def test_wind_speed_100(self):
        self.shack.set_wind_speed(100.2)
        self.assertEqual(self.shack.wind_speed, 100.2)

    def test_wind_speed(self):
        # No changes
        self.shack.wind_gust = 0
        self.shack.max_wind_gust = 0
        self.shack.set_wind_gust(0)
        self.assertEqual(self.shack.wind_gust, 0)
        self.assertEqual(self.shack.max_wind_gust, 0)

        # Max should not change
        self.shack.wind_gust = 0
        self.shack.max_wind_gust = 5.0
        self.shack.set_wind_gust(0)
        self.assertEqual(self.shack.wind_gust, 0)
        self.assertEqual(self.shack.max_wind_gust, 5.0)

        # Max should not change
        self.shack.wind_gust = 5
        self.shack.max_wind_gust = 6
        self.shack.set_wind_gust(5)
        self.assertEqual(self.shack.wind_gust, 5)
        self.assertEqual(self.shack.max_wind_gust, 6)

        # Max should not change
        self.shack.wind_gust = 5
        self.shack.max_wind_gust = 5
        self.shack.set_wind_gust(10.5)
        self.assertEqual(self.shack.wind_gust, 10.5)
        self.assertEqual(self.shack.max_wind_gust, 10.5)

    def test_set_wind_cardinal(self):
        self.shack.set_wind_cardinal("NbW")
        self.assertEqual(self.shack.wind_cardinal, "NbW")

    def test_set_temperature(self):
        # All equal
        self.shack.set_temperature(10)
        self.assertEqual(self.shack.temperature, 10)
        self.assertEqual(self.shack.min_temperature, 10)
        self.assertEqual(self.shack.max_temperature, 10)

        # Max should increase
        self.shack.set_temperature(15)
        self.assertEqual(self.shack.temperature, 15)
        self.assertEqual(self.shack.min_temperature, 10)
        self.assertEqual(self.shack.max_temperature, 15)

        # Min should decrease
        self.shack.set_temperature(5)
        self.assertEqual(self.shack.temperature, 5)
        self.assertEqual(self.shack.min_temperature, 5)
        self.assertEqual(self.shack.max_temperature, 15)

        self.shack.set_temperature(-0.56)
        self.assertEqual(self.shack.temperature, -0.56)
        self.assertEqual(self.shack.min_temperature, -0.56)
        self.assertEqual(self.shack.max_temperature, 15)

        self.shack.set_temperature(-1.67)
        self.assertEqual(self.shack.temperature, -1.67)
        self.assertEqual(self.shack.min_temperature, -1.67)
        self.assertEqual(self.shack.max_temperature, 15)

    def test_set_humidity(self):
        # All equal
        self.shack.set_humidity(10)
        self.assertEqual(self.shack.humidity, 10)
        self.assertEqual(self.shack.min_humidity, 10)
        self.assertEqual(self.shack.max_humidity, 10)

        # Max should increase
        self.shack.set_humidity(15)
        self.assertEqual(self.shack.humidity, 15)
        self.assertEqual(self.shack.min_humidity, 10)
        self.assertEqual(self.shack.max_humidity, 15)

        # Min should decrease
        self.shack.set_humidity(5)
        self.assertEqual(self.shack.humidity, 5)
        self.assertEqual(self.shack.min_humidity, 5)
        self.assertEqual(self.shack.max_humidity, 15)

    def test_set_pressure(self):
        # All equal
        self.shack.set_pressure(10.5)
        self.assertEqual(self.shack.pressure, 10.5)
        self.assertEqual(self.shack.min_pressure, 10.5)
        self.assertEqual(self.shack.max_pressure, 10.5)
        self.assertEqual(self.shack.pressure_direction, '')

        # Max should increase
        self.shack.set_pressure(15)
        self.assertEqual(self.shack.pressure, 15)
        self.assertEqual(self.shack.min_pressure, 10.5)
        self.assertEqual(self.shack.max_pressure, 15)
        self.assertEqual(self.shack.pressure_direction, ' and rising ')

        # Min should decrease
        self.shack.set_pressure(5)
        self.assertEqual(self.shack.pressure, 5)
        self.assertEqual(self.shack.min_pressure, 5)
        self.assertEqual(self.shack.max_pressure, 15)
        self.assertEqual(self.shack.pressure_direction, ' and falling ')

        # Min should decrease
        self.shack.set_pressure(5)
        self.assertEqual(self.shack.pressure, 5)
        self.assertEqual(self.shack.min_pressure, 5)
        self.assertEqual(self.shack.max_pressure, 15)
        self.assertEqual(self.shack.pressure_direction, ' ')

        # Min should decrease
        self.shack.set_pressure(4)
        self.assertEqual(self.shack.pressure, 4)
        self.assertEqual(self.shack.min_pressure, 4)
        self.assertEqual(self.shack.max_pressure, 15)
        self.assertEqual(self.shack.pressure_direction, ' and falling ')

        # Max should increase
        self.shack.set_pressure(10)
        self.assertEqual(self.shack.pressure, 10)
        self.assertEqual(self.shack.min_pressure, 4)
        self.assertEqual(self.shack.max_pressure, 15)
        self.assertEqual(self.shack.pressure_direction, ' and rising ')

    def test_set_pv_watts(self):
        self.shack.pv_watts = 0
        self.shack.pv_samples = 1
        self.shack.pv_total = 100
        self.shack.pv_average = 100
        self.shack.set_pv_watts(0)
        self.assertEqual(self.shack.pv_watts, 0)
        self.assertEqual(self.shack.pv_samples, 1)
        self.assertEqual(self.shack.pv_total, 100)
        self.assertEqual(self.shack.pv_average, 100)

        self.shack.sun = True
        self.shack.set_pv_watts(150)
        self.assertEqual(self.shack.pv_watts, 150)
        self.assertEqual(self.shack.pv_samples, 2)
        self.assertEqual(self.shack.pv_total, 250)
        self.assertEqual(self.shack.pv_average, 125)

    # Not sure how useful this is
    def test_time_stamp(self):
        self.assertTrue(self.timestamp, self.shack.time_stamp())

    def test_reset_max_min(self):
        today = date.today()
        self.shack.pv_average = 10
        today = date.today()
        # Yesterday, 23:59
        self.shack.today = datetime(today.year, today.month, today.day - 1, 23, 59, 00)
        # Today 16 seconds past midnight
        self.assertTrue(self.shack.reset_max_min(datetime(today.year, today.month, today.day, 00, 00, 16)))
        # No need to check all of them
        self.assertEqual(self.shack.wind_speed, 0)
        self.assertEqual(self.shack.pv_average, 0)
        self.assertEqual(self.shack.today, date.today())

        # Try again at 15 seconds past the hour, should be false
        self.shack.today = date.today()
        self.assertFalse(self.shack.reset_max_min(datetime(today.year, today.month, today.day, 00, 00, 15)))

    def test_check_sun_up(self):
        # Set up
        o = ephem.Observer()
        o.lat = '51.1661'
        o.long = '-7.1608'
        s = ephem.Sun()
        s.compute()
        self.next_rising = ephem.localtime(o.next_rising(s))
        self.next_setting = ephem.localtime(o.next_setting(s))
        self.shack.next_rising = self.next_rising
        self.shack.next_setting = self.next_setting
        now = datetime.now()
        # Case 1. After Sunrise
        if now < self.next_setting and self.shack.today == date.today():
            self.assertTrue(self.shack.check_sun_up(now))
        # Are we before sunrise or after sunset?
        #if now < self.shack.next_rising or now > self.shack.next_setting:
        #    self.assertFalse(self.shack.check_sun_up(now))
        # Case 2 
        if self.next_rising <= now <= self.next_setting:
            # Sun should be up so
            self.assertTrue(self.shack.check_sun_up(now))

    def test_set_wind_direction(self):
        # > 360 not possible
        with self.assertRaises(ValueError):
            self.shack.set_wind_direction(361)
        # Only testing a few possibilities
        self.shack.set_wind_direction("200")
        self.assertEqual(self.shack.wind_cardinal, "SSW")
        self.shack.set_wind_direction(360)
        self.assertEqual(self.shack.wind_cardinal, "N")
        #
        self.shack.set_wind_direction(200)
        self.assertEqual(self.shack.wind_cardinal, "SSW")
        #
        self.shack.set_wind_direction(100)
        self.assertEqual(self.shack.wind_cardinal, "EbS")

    def test_process_pv_messages(self):
        # Morning no Sun
        self.shack.process_pv_messages(0)
        self.assertEqual(self.shack.pv_watts, 0)
        self.assertEqual(self.shack.pv_samples, 0)
        self.assertEqual(self.shack.pv_total, 0)
        self.assertEqual(self.shack.pv_average, 0)
        # Set Sunrise times to just before and just after now
        now = datetime.now()

        self.shack.next_rising = now - timedelta(hours=1)
        self.shack.next_setting = now + timedelta(hours=1)

        # Sun is artifically up now, should get good morning
        self.shack.sun = True
        self.shack.process_pv_messages(100)
        self.assertEqual(self.shack.pv_watts, 100)
        self.assertEqual(self.shack.sun_state, 1)

        self.shack.process_pv_messages(100)
        self.assertEqual(self.shack.pv_watts, 100)
        self.assertEqual(self.shack.sun_state, 1)

        # Should get Woops
        self.shack.process_pv_messages(0)
        self.assertEqual(self.shack.pv_watts, 0)
        self.assertEqual(self.shack.sun_state, 2)

        self.shack.process_pv_messages(0)
        self.assertEqual(self.shack.pv_watts, 0)
        self.assertEqual(self.shack.sun_state, 2)

        # Should get welcome
        self.shack.process_pv_messages(100)
        self.assertEqual(self.shack.pv_watts, 100)
        self.assertEqual(self.shack.sun_state, 3)

        self.shack.process_pv_messages(100)
        self.assertEqual(self.shack.pv_watts, 100)
        self.assertEqual(self.shack.sun_state, 3)

        # Need to test for state 4
        # Should get welcome
        
        self.shack.process_pv_messages(0)
        self.assertEqual(self.shack.pv_watts, 0)
        self.assertEqual(self.shack.sun_state, 3)
        self.shack.sun = False
        self.shack.process_pv_messages(0)
        self.assertEqual(self.shack.pv_watts, 0)
        self.assertEqual(self.shack.sun_state, 0)

    # Tested using wind_speed thresholds.
    def test_ok_send_wx(self):
        # setup
        temp = datetime.today()
        # If Max/Min are the same ok_send_wx will fail.
        self.shack.set_temperature(10)
        self.shack.set_temperature(9)
        hours = ['0', '2', '4', '6', '8', '10', '12',
                      '14', '16', '18', '20', '22']
        for hour in hours:
            now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
            # Should be ok to print on an even 2 hour time
            self.assertTrue(self.shack.ok_send_wx(now))

        hours = ['1', '3', '5', '7', '9', '11',
                      '13', '15', '17', '19', '21', '23']

        for hour in hours:
            now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
            # Should be ok to print on an even 2 hour time
            self.assertFalse(self.shack.ok_send_wx(now))

        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']

        # Level 1 should kick in hourly updates
        self.shack.set_wind_speed(51/3.6)
        #self.shack.max_temperature = 1
        #self.shack.set_temperature(-4)
        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22', '23']
        for hour in hours:
            now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
            self.assertTrue(self.shack.ok_send_wx(now))

        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['15', '30', '45']
        for hour in hours:
            for minute in minutes:
                now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                self.assertFalse(self.shack.ok_send_wx(now))

        # Level 2 should kick in 30 minute updates
        #self.shack.min_temperature = 21
        #self.shack.max_temperature = 22
        #self.shack.set_temperature(23)
        self.shack.set_wind_speed(66/3.6)
        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['0', '30']
        for hour in hours:
            for minute in minutes:
                now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                self.assertTrue(self.shack.ok_send_wx(now))

        # Nothing should appear at 15 and 45 min intervals
        self.shack.set_wind_speed(66/3.6)
        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['15', '45']
        for hour in hours:
            for minute in minutes:
                now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                self.assertFalse(self.shack.ok_send_wx(now))

        # Level 3 15 minute intervals
        self.shack.set_wind_speed(81/3.6)
        #self.shack.set_temperature = float(-30)
        #self.shack.set_temperature = float(-20)
        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['0', '15', '45']
        for hour in hours:
            for minute in minutes:
                now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                self.assertTrue(self.shack.ok_send_wx(now))

        self.shack.min_temperature = 0
        self.shack.max_temperature = 0
        print "Calling send_wx_message"
        self.shack.send_wx_message(now)
        self.assertFalse(self.shack.ok_send_wx(now))

    # Gated by test_ok_send_wx so no need for second or minute limit
    def test_ok_send_rising(self):
        temp = datetime.today()
        # Set sunrise to 08:23
        self.shack.next_rising = datetime(temp.year,
                                          temp.month,
                                          temp.day, 8, 23)
        # 3am should be false
        now = datetime(temp.year, temp.month, temp.day, 04, 15)
        self.assertTrue(self.shack.ok_send_rising(now))
        # # 4:00:10 should be True
        now = datetime(temp.year, temp.month, temp.day, 06, 00, 15)
        self.assertTrue(self.shack.ok_send_rising(now))
        self.shack.send_wx_message(now)
        # # 8:00:10 am should still be true
        now = datetime(temp.year, temp.month, temp.day, 8, 00, 10)
        self.assertTrue(self.shack.ok_send_rising(now))
        # # 12:00:10 should be false
        now = datetime(temp.year, temp.month, temp.day, 12, 00, 15)
        self.assertFalse(self.shack.ok_send_rising(now))

    # Gated by test_ok_send_wx so no need for second or minute limits
    def test_ok_send_setting(self):
        temp = datetime.today()
        # Set sunrise to 08:23
        self.shack.next_setting = datetime(temp.year,
                                           temp.month,
                                           temp.day, 18, 23)
        # As long as sun is up. Anytime should be ok.
        now = datetime(temp.year, temp.month, temp.day, 12, 00, 15)
        self.assertTrue(self.shack.ok_send_setting(now))
        self.shack.send_wx_message(now)
        # should be False
        now = datetime(temp.year, temp.month, temp.day, 04, 00, 0)
        self.assertTrue(self.shack.ok_send_setting(now))
        # should be false
        now = datetime(temp.year, temp.month, temp.day, 23, 00, 00)
        self.assertFalse(self.shack.ok_send_setting(now))

    def test_ok_send_telemetry(self):
        temp = datetime.today()

        # Sun not up yet. False
        now = datetime(temp.year, temp.month, temp.day, 06, 45, 20)
        self.assertFalse(self.shack.ok_send_telemetry(now))
        #
        now = datetime(temp.year, temp.month, temp.day, 12, 45, 20)
        self.shack.sun_up()
        # Midday, sun should be up, pv_watts is 0
        self.assertFalse(self.shack.ok_send_telemetry(now))
        #
        now = datetime(temp.year, temp.month, temp.day, 13, 45, 00)
        self.assertFalse(self.shack.ok_send_telemetry(now))
        # Should fail
        now = datetime(temp.year, temp.month, temp.day, 13, 25, 20)
        self.assertFalse(self.shack.ok_send_telemetry(now))

    def test_other_functions(self):
        now = datetime.now()
        self.shack.pv_average = 100
        self.shack.pv_watts = 120
        print "Calling send_telemetry_message"
        self.shack.send_telemetry_message(now)
        print "Calling process_sat_messages"
        self.shack.process_sat_messages("Sat pluto")
        self.shack.process_sat_messages("Sat ISS visible")

        # Midday should be false

    def test_gust_warnings(self):
        temp = datetime.today()
        self.shack.set_wind_gust(89/3.6)
        # Need a temp that isn't 0
        self.shack.set_temperature(10)
        # Level 0 Wind Alert should print wx info on the 60 minute mark
        # Just below thresholds
        self.shack.set_wind_gust(89/3.6)
        self.shack.set_temperature(10)
        self.shack.set_temperature(9)
        hours = ['0', '2', '4', '6', '8', '10', '12',
                      '14', '16', '18', '20', '22']
        for hour in hours:
            now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
            # Should be ok to print on an even 2 hour time
            self.assertTrue(self.shack.ok_send_wx(now))

        hours = ['1', '3', '5', '7', '9', '11',
                      '13', '15', '17', '19', '21', '23']

        for hour in hours:
            now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
            # Should be ok to print on an even 2 hour time
            self.assertFalse(self.shack.ok_send_wx(now))
        # Level 1 Wind Gust
        self.shack.set_wind_gust(90/3.6)
        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22', '23']
        for hour in hours:
            now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
            self.assertTrue(self.shack.ok_send_wx(now))
            self.assertTrue(self.shack.wind_gust_warning, 1)

        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['15', '30', '45']
        for hour in hours:
            for minute in minutes:
                now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                self.assertFalse(self.shack.ok_send_wx(now))
                self.assertTrue(self.shack.wind_gust_warning, 1)
        # Level 2 Wind Gust
        self.shack.set_wind_gust(110/3.6)

        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['0', '30']
        for hour in hours:
            for minute in minutes:
                now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                self.assertTrue(self.shack.ok_send_wx(now))
                self.assertTrue(self.shack.wind_gust_warning, 2)

        # Level 3 Wind Gust
        self.shack.set_wind_gust(130/3.6)
        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['0', '15', '45']
        for hour in hours:
            for minute in minutes:
                now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                self.assertTrue(self.shack.ok_send_wx(now))
                self.assertTrue(self.shack.wind_gust_warning, 3)

    def test_temp_warnings(self):
        temp = datetime.today()
        # 19 is just below threshold
        self.shack.set_temperature(-2)
        self.shack.set_temperature(+3)
        self.shack.set_wind_direction(100)
        # Level 0 Temperature should print wx info on the 60 minute mark
        # Just below thresholds
        self.shack.set_temperature(4)
        #self.shack.set_temperature(1)
        # Level 0 Temperature should print wx info on the 60 minute mark
        # Just below thresholds
        collection = ['3', '2', '1', '0', '-1', '-2']

        hours = ['0', '2', '4', '6', '8', '10', '12',
                      '14', '16', '18', '20', '22']

        for x in collection:
            self.shack.set_temperature(x)
            for hour in hours:
                now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
                # Should be ok to print on an even 2 hour time
                self.assertTrue(self.shack.ok_send_wx(now))
                self.assertEqual(self.shack.temp_warning, 0)

        hours = ['1', '3', '5', '7', '9', '11',
                 '13', '15', '17', '19', '21', '23']
        for hour in hours:
            now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
            # Should be ok to print on an even 2 hour time
            self.assertFalse(self.shack.ok_send_wx(now))
            self.assertEqual(self.shack.temp_warning, 0)

        # Level 1 Set Max/Min
        self.shack.min_temperature = 1
        self.shack.max_temperature = 1
        collection = ['-4', '-3']
        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22', '23']
        for x in collection:
            self.shack.set_temperature(x)
            for hour in hours:
                now = datetime(temp.year, temp.month, temp.day, int(hour), 00, 15)
                self.assertTrue(self.shack.ok_send_wx(now))
                self.assertEqual(self.shack.temp_warning, 1)

        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['15', '30', '45']
        for x in collection:
            self.shack.set_temperature(x)
            for hour in hours:
                for minute in minutes:
                    now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                    self.assertFalse(self.shack.ok_send_wx(now))
                    self.assertEqual(self.shack.temp_warning, 1)

        # Level 2 Set Max/Min
        self.shack.min_temperature = -8
        self.shack.max_temperature = -1
        collection = ['-8', '-7', '-6', '-5']

        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22', '23']
        minutes = ['0', '30']
        for x in collection:
            self.shack.set_temperature(x)
            for hour in hours:
                for minute in minutes:
                    now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                    self.assertTrue(self.shack.ok_send_wx(now))
                    self.assertEqual(self.shack.temp_warning, 2)

        # Level 3
        self.shack.min_temperature = -11
        self.shack.max_temperature = -10
        collection = ['-10', '-11', '-12', '-13', '-14']
        hours = ['0', '1', '2', '3', '4', '5', '6', '8', '9', '10', '11',
                      '12', '13', '14', '15', '16', '17', '18', '19', '20',
                      '21', '22']
        minutes = ['0', '15', '45']
        for x in collection:
            self.shack.set_temperature(x)
            for hour in hours:
                for minute in minutes:
                    now = datetime(temp.year, temp.month, temp.day, int(hour), int(minute), 15)
                    self.assertTrue(self.shack.ok_send_wx(now))
                    self.assertEqual(self.shack.temp_warning, 3)

if __name__ == '__main__':
    unittest.main()
