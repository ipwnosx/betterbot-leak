import sys
import re
import recaptcha
import requests
import json
import random
import Queue
import threading

emails_q = Queue.Queue()

def debug(text, conf):
  if conf['debug']:
    print("[DEBUG]" + str(text))

def read_configurations():
  try:
    conf = json.loads(open('discord_verify.json', 'r').read())
    print("Loaded configs with values:")
    print("\temails_file: " + str(conf['emails_file']))
    print("\toutput_file: " + str(conf['output_file']))
    print("\ttimeout: " + str(conf['timeout']))
    print("\tnb_threads: " + str(conf['nb_threads']))
    print("\tdebug: " + str(conf['debug']))
    return conf
  except Exception as e:
    print(e)
sys.exit(1)

def array_to_queue(arr, q):
  for i in arr:
    q.put(i)
  return q

def save_user(email, password, conf):
  debug("saving user", conf)
output = open(conf['output_file'], 'a')
output.write(":".join(
  [email, password]
) + "\n")
output.close()

def get_headers():
  return {
    'user-agent': 'Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16',
    'Host': 'discordapp.com',
    'Accept': '*/*',
    'Accept-Language': 'en-US',
    'Content-Type': 'application/json',
    'Referer': 'https://discordapp.com/register',
    'DNT': '1',
    'Connection': 'keep-alive'
  }

def verify(email, password, conf):
  debug("verifying : " + email + " " + password, conf)
headers = get_headers()
ss = requests.Session()
debug("opening email", conf)
response = ss.post('https://auth.mail.ru/cgi-bin/auth', {
  'post': None,
  'mhost': 'mail.ru',
  'login_from': None,
  'Login': email,
  'Domain': 'mail.ru',
  'Password': password
})
text = response.text.encode('utf-8').replace("\n", "")
debug("trying to find link", conf)
open('MAILRU.html', 'w').write(text)
link = re.findall('id: "(\d+)",\s*prev:\s*"\d*",\s*next:\s*"\d*",\s*subject:\s*u\("Verify Email Address for Discord"\)', text)[0]
debug("found email link: " + link, conf)
response = ss.get('https://m.mail.ru/message/{0}'.format(link))
activation = re.findall('url=(https%3A%2F%2Fdiscordapp.com%2Fverify[^"]+)"', response.text.encode('utf-8'))[0]
activation = requests.utils.unquote(activation)
debug("found activation link: " + activation, conf)
token = re.findall("token=([^&]+)&", activation)[0]
debug("token is " + token, conf)
debug("opening activation link", conf)
ss.get(activation,
  headers = headers,
  timeout = conf['timeout'])
debug("fetching a captcha", conf)
captcha = recaptcha.GetCaptcha()
payload = {
  'token': token,
  'captcha_key': captcha
}
debug("sending payload:" + str(payload), conf)
response = ss.post(
  'https://discordapp.com/api/v6/auth/verify',
  json = payload,
  headers = headers,
  timeout = conf['timeout']
)

def worker(conf):
  debug("worker started", conf)
while not emails_q.empty():
  email_pwd = emails_q.get()
emails_q.task_done()
email = email_pwd.split(":")[0]
e_password = email_pwd.split(":")[1]
try:
  verify(email, e_password, conf)
  save_user(email, e_password, conf)
except Exception as e:
  print (e)
debug("could not verify " + str(e.message), conf)

def main():
  global emails_q
print("Starting")
conf = read_configurations()
data = [x.rstrip() for x in open(conf['emails_file'], 'r').readlines()]
emails = []
alreadydone = [x.rstrip() for x in open(conf['output_file'], 'r').readlines()]
for _ in data:
  try:
    email = _.split(':')[2] + ':' + _.split(':')[3]
    if email not in alreadydone:
      emails.append(email)
  except:
    pass
emails_q = array_to_queue(emails, emails_q)
tx = []
debug("Starting " + str(conf['nb_threads']) + " threads", conf)
for i in range(conf['nb_threads']):
  mT = threading.Thread(target = worker, args = (conf, ))
mT.start()
tx.append(mT)
for t in tx:
  t.join()
print("Finished")

if __name__ == "__main__":
  while 1:
    main()