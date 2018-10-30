import urllib
import traceback


def send_sms(number, message):
    error = 0
    url = 'https://control.msg91.com/api/sendhttp.php?authkey=77123ATu6JCJlW3I554a7f9d3&mobiles=%s&message=%s&sender=MIEBAC&route=4'
    url = url % (number, urllib.quote(message))
    try:
        data = urllib.urlopen(url).read()
    except Exception as e:
        data = traceback.format_exc()
        error = 1

    return data, error
