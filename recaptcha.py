import requests
import time
try:
	from urllib import quote_plus
except ImportError:
	from urllib.parse import quote_plus

sitekey = '6Lef5iQTAAAAAKeIvIY-DeexoO3gj7ryl9rLMEnn'

API_KEY = open('api.txt').read().rstrip()
url = quote_plus('https://discordapp.com/register')

def GetCaptcha(ID=None, times=0):
    try:
        captcha_id = None
        s = requests.Session()
        if ID==None:
            captcha_id = s.get("http://2captcha.com/in.php?key={0}&method=userrecaptcha&googlekey={1}&pageurl={2}".format(API_KEY, sitekey, url), timeout=5).text.split('|')[1]
            if(captcha_id == 'ERROR_ZERO_BALANCE'):
                print("No balance")
        else:
            captcha_id = ID
        print ("Solving Captcha...")
        print ("Please wait...")
        while 1:
            if times>=30:
                return GetCaptcha()
            
            recaptcha_answer = s.get("http://2captcha.com/res.php?key={}&action=get&id={}".format(API_KEY, captcha_id), timeout=15)
            if recaptcha_answer.status_code != 200:
                time.sleep(5)
                times+=1
                continue
            if 'CAPCHA_NOT_READY' not in recaptcha_answer.text:
                break
            time.sleep(5)
            times+=1
        if(recaptcha_answer.text == 'ERROR_CAPTCHA_UNSOLVABLE'):
            return GetCaptcha()
        else:
            print ("Captcha SOLVED")
            answer = recaptcha_answer.text.split('|')[1]
            return answer
    except Exception as e:
        print (e)
        time.sleep(5)
        return GetCaptcha(captcha_id, times)
