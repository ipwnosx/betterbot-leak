import sys
import re
import recaptcha
import requests
import json
import random
import Queue
import threading

emails_q = Queue.Queue()
proxies_q = Queue.Queue()

def debug(text, conf):
    if conf['debug']:
        print ("[DEBUG] "+ str(text))

def read_configurations():
    try:
        conf = json.loads(open('discord_register.json','r').read())
        print ("Loaded configs with values:")
        print ("\temails_file: " + str(conf['emails_file']))
        print ("\toutput_file: " + str(conf['output_file']))
        print ("\tproxy_file: " + str(conf['proxy_file']))
        print ("\tproxy_blacklist_file: " + str(conf['proxy_blacklist_file']))
        print ("\ttimeout: " + str(conf['timeout']))
        print ("\tnb_threads: " + str(conf['nb_threads']))
        print ("\tdebug: " + str(conf['debug']))
        return conf
    except:
        print ("ERROR")
        sys.exit(1)

def array_to_queue(arr, q):
    for i in arr:
        q.put(i)
    return q

def save_user(email, username, password, discriminator, email_password, api_key, conf):
    debug("saving user", conf)
    output = open(conf['output_file'], 'a')
    output.write(":".join(
        [discriminator, password, email, email_password]
        )+"\n")
    output.flush()
    output.close()
    output = open(conf['output_token_file'], 'a')
    output.write(api_key+"\n")
    output.flush()
    output.close()

def generate_user_pass_pair():
    starts = ['touches_','loves_','hates_','licks_','feels_', 'moves_', 'dances_' , 'swipes_', 'kills_', 'trickles_', 'pierces_', 'bananas_', 'quicks_']
    verbs = ['awkward','thin','thick','happy','sad','tall','short','malious','ravenous','smooth','loving','mean','weird','high','sober',"smart",'dumb','rich','poor','mega','music','lord', 'uber', 'magician', 'insane', 'genius', 'incredible']
    nouns = ['hacker','lumberjack','horse','unicorn','guy','girl','man','woman','male','female','men','women','duck','dog','sheep','zombie','tennis','doctor', 'cattle', 'zombie', 'monster', 'destroyer', 'v', 'a','b','c','d']
    random_touch = random.randint(1,1000)
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    pw_length = 12
    mypw = ""
    for i in range(pw_length):
        next_index = random.randrange(len(alphabet))
        mypw = mypw + alphabet[next_index]
    return (random.choice(starts) + random.choice(verbs) + '_' + random.choice(nouns) + str(random_touch), mypw)

def set_proxy(session, proxy):
    if proxy != 'none':
        session.proxies.update({
            'http:' : 'http://' + proxy,
            'https:' : 'https://' + proxy
        })
    return session

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


def register(email, e_password, proxy, conf):
    headers = get_headers()
    s = requests.Session()
    #ss = set_proxy(ss, proxy)
    print (proxy)
    if proxy != 'none':
        proxies = {
            'http' : 'http://' + proxy,
            'https' : 'https://' + proxy
        }
        s.proxies.update(proxies)
    fingerprint_json = s.get(
        "https://discordapp.com/api/v6/experiments",
        timeout=conf['timeout'],
        headers=headers
    ).text
    fingerprint = json.loads(fingerprint_json)["fingerprint"]
    debug(fingerprint, conf)

    headers['X-Fingerprint'] = fingerprint
    (username, password) = generate_user_pass_pair()
    payload = {
        'fingerprint': fingerprint,
        'email': email,
        'username': username,
        'password': password,
        'invite': None,
        'captcha_key': None
    }
    debug("first registration post "+email+":"+username+":"+password, conf)
    response = s.post(
        'https://discordapp.com/api/v6/auth/register',
        json=payload,
        headers=headers,
        timeout=conf['timeout']
    )
    debug(response.json(), conf)

    if 'captcha-required' in response.text:
        debug("captcha required -> account will be created (might lead to bug if captcha response isn't valid", conf)
    if 'You are being rate limited.' in response.text:
        debug("You are being rate limited.", conf)
        return False
    if 'Email is already registered.' in response.text:
        debug("Already registered", conf)
        return True

    debug("fetching captcha", conf)
    captcha = recaptcha.GetCaptcha()
    debug("result is: "+captcha, conf)
    payload['captcha_key'] = captcha
    debug("sending payload:"+str(payload), conf)
    response = s.post(
        'https://discordapp.com/api/v6/auth/register',
        json=payload,
        headers=headers,
        timeout=conf['timeout']
    )
    debug(response.json(), conf)
    if 'unauthorize' in response.text:
        debug('unauthorized', conf)
        return False
    api_key = response.json()['token']
    headers['Authorization'] = api_key
    debug("login in and fetching token/api key", conf)
    response = s.get(
        'https://discordapp.com/api/v6/users/@me',
        headers=headers,
        timeout=conf['timeout']
    )
    debug(response.json(), conf)
    discriminator = response.json()['discriminator']
    save_user(email, username, password, discriminator, e_password, api_key, conf)
    return True

def verify(email, password, proxy, conf):
    debug("verifying : "+email+" "+password, conf)
    headers = get_headers()
    ss = requests.Session()

    ss = set_proxy(ss, proxy)
    debug("opening email", conf)
    response  = ss.post('https://auth.mail.ru/cgi-bin/auth', {
        'post':None, 
        'mhost': 'mail.ru',
        'login_from': None,
        'Login': email,
        'Domain': 'mail.ru',
        'Password': password})
    text = response.text.encode('utf-8').replace("\n","")
    debug("trying to find link", conf)
    open('MAILRU.html','w').write(text)
    link = re.findall('id: "(\d+)",\s*prev:\s*"\d*",\s*next:\s*"\d*",\s*subject:\s*u\("Verify Email Address for Discord"\)',text)[0]
    debug("found email link: "+link, conf)
    response = ss.get('https://m.mail.ru/message/{0}'.format(link))
    activation = re.findall('url=(https%3A%2F%2Fdiscordapp.com%2Fverify[^"]+)"', response.text.encode('utf-8'))[0]
    activation = requests.utils.unquote(activation)
    debug("found activation link: "+activation, conf)
    token = re.findall("token=([^&]+)&", activation)[0]
    debug("token is "+token, conf)
    debug("opening activation link", conf)
    ss.get(activation,
        headers=headers,
        timeout=conf['timeout'])
    debug("fetching a captcha", conf)
    captcha = recaptcha.GetCaptcha()
    payload = {
        'token' : token,
        'captcha_key' : captcha
    }
    debug("sending payload:"+str(payload), conf)
    response = ss.post(
        'https://discordapp.com/api/v6/auth/verify',
        json=payload,
        headers=headers,
        timeout=conf['timeout']
    )
    return True


def worker(conf, black_proxies):
    debug("worker started", conf)
    already_registered = []
    while not emails_q.empty():
        proxies_used_file = 'usedproxies.txt'
        try:
            proxies_used = open(proxies_used_file).read()
        except:
            proxies_used = ''
      
        proxy = proxies_q.get()
        proxies_q.put(proxy)
        proxies_q.task_done()
        if proxies_used.count(proxy) > 3:
            continue
        email_pwd = emails_q.get()
        emails_q.task_done()
        email = email_pwd.split(":")[0]
        e_password = email_pwd.split(":")[1]
        #while proxy in black_proxies:
         #   proxy = proxies_q.get()
         #   proxies_q.task_done()
        debug("trying to create "+email+" with proxy "+proxy, conf)
        try:
            could_register = register(email, e_password, proxy, conf)
            """
            put the save here
            save also email in output for the verify script
            """
            # if could not register we re-add the email
            if not could_register:
                debug("couldn't register -> readding email", conf)
                emails_q.put(email_pwd)
            open(proxies_used_file,'a').write(proxy+'\n')
            #else:
            #    try:
            #        could_verify = verify(email, e_password, proxy, conf)
            #    except Exception, e:
            #        print e
            #        debug("could not verify "+e.message, conf)
        except:
            black_proxies.append("ERROR2")

        #if it reaches this point then it means that the proxy was fine


def main():
    global emails_q
    global proxies_q
    print ("Starting")
    conf = read_configurations()
    emails2 = [x.rstrip() for x in open(conf['emails_file'], 'r').readlines()]
    alreadydone = [x.rstrip().split(':')[0] for x in open(conf['output_file']).readlines()]
    emails = []
    for email in emails2:
        m = email.split(':')[0]
        if m not in alreadydone:
            emails.append(email)
    emails_q = array_to_queue(emails, emails_q)
    proxies = [x.rstrip() for x in open(conf['proxy_file'], 'r').readlines()]
    proxies_q = array_to_queue(proxies, proxies_q)
    black_proxies = [x.rstrip() for x in open(conf['proxy_blacklist_file'], 'r').readlines()]
    tx = []
    debug("Starting "+str(conf['nb_threads'])+" threads", conf)
    for i in range(conf['nb_threads']):
        mT = threading.Thread(target=worker, args=(conf, black_proxies))
        mT.start()
        tx.append(mT)
    for t in tx:
        t.join()
    print ("Finished")

if __name__ == "__main__":
    while 1:
        main()
