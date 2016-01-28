# mqtt2notify 

A small program using MQTT to listen to the output of various processes running locally and spit them out as desktop notifications.  Given the right credentials. It will also tweet.

## Config file

    [twitter]
    consumer_key = <consumer_key>
    consumer_secret = <consumer_secret>
    access_key = <access_key>
    access_secret = <access_secret>
    tweet = False

    [mqtt]
    server = 127.0.0.1
    port = 1883
    clientname = mqtt2notify
    
    [gps]
    lat = 52.0000
    long = -7.0000

    [logging]
    level = logging.INFO
