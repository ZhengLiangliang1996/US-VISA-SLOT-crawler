#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2022 liangliang <liangliang@Liangliangs-MacBook-Air.local>
#
# Distributed under terms of the MIT license.
# -*- coding: utf8 -*-

import time
import json
import random
import platform
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from telegram import send_message
from creds import username, password, url_id

USERNAME = username
PASSWORD = password
SCHEDULE = url_id

PUSH_TOKEN = '<my push token>'
PUSH_USER = '<my push user>'

MY_SCHEDULE_DATE = "2022-08-31" # 2020-12-02
MY_CONDITION = lambda month,day: int(month) == 7 or int(month) == 8 or int(month) == 6

SLEEP_TIME = 60*2   # recheck time interval

# VISA website for belgium, should be changed according to your regin, 42 is the 
# facility id, could be found by searching 'ata-collects-biometrics' in page source code
DATE_URL = "https://ais.usvisa-info.com/en-be/niv/schedule/%s/appointment/days/42.json?appointments[expedite]=false" % SCHEDULE
TIME_URL = "https://ais.usvisa-info.com/en-be/niv/schedule/%s/appointment/times/42.json?date=%%s&appointments[expedite]=false" % SCHEDULE
APPOINTMENT_URL = "https://ais.usvisa-info.com/en-be/niv/schedule/%s/appointment" % SCHEDULE
HUB_ADDRESS = 'http://localhost:4444/wd/hub'
EXIT = False


def send(msg):
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": PUSH_TOKEN,
        "user": PUSH_USER,
        "message": msg
    }
    requests.post(url, data)


def get_drive():
    drive = webdriver.Chrome(ChromeDriverManager().install())
    return drive 

driver = get_drive()


def login(url):
    # Bypass reCAPTCHA
    driver.get(url)
    time.sleep(1)
    print(driver.current_url)
    if driver.current_url == 'https://ais.usvisa-info.com/en-be/niv/users/sign_in':
        do_login_action()


def do_login_action():
    print('Logging in.')
    # Clicking the first prompt, if there is one
    try:
        driver.find_element_by_xpath('/html/body/div[6]/div[3]/div/button').click()
    except:
        pass
    # Filling the user and password
    user_box = driver.find_element_by_name('user[email]')
    user_box.send_keys(USERNAME)
    password_box = driver.find_element_by_name('user[password]')
    password_box.send_keys(PASSWORD)
        # Clicking the checkbox
    driver.find_element_by_xpath('//*[@id="new_user"]/div[3]/label/div').click()
        # Clicking 'Sign in'
    driver.find_element_by_xpath('//*[@id="new_user"]/p[1]/input').click()

    #Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(),'Continue')]")))
    time.sleep(5)
    print("Login successfully! ")


def get_date():
    driver.get(DATE_URL)
    if not is_logined():
        login()
        return get_date()
    else:
        content = driver.find_element_by_tag_name('pre').text
        date = json.loads(content)
        return date


def get_time(date):
    time_url = TIME_URL % date
    driver.get(time_url)
    content = driver.find_element_by_tag_name('pre').text
    data = json.loads(content)
    time = data.get("available_times")[-1]
    print("Get time successfully!")
    return time


def reschedule(date):
    global EXIT
    print("Start Reschedule")

    time = get_time(date)
    driver.get(APPOINTMENT_URL)

    data = {
        "utf8": driver.find_element_by_name('utf8').get_attribute('value'),
        "authenticity_token": driver.find_element_by_name('authenticity_token').get_attribute('value'),
        "confirmed_limit_message": driver.find_element_by_name('confirmed_limit_message').get_attribute('value'),
        "use_consulate_appointment_capacity": driver.find_element_by_name('use_consulate_appointment_capacity').get_attribute('value'),
        "appointments[consulate_appointment][facility_id]": "42",
        "appointments[consulate_appointment][date]": date,
        "appointments[consulate_appointment][time]": time,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36",
        "Referer": APPOINTMENT_URL,
        "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
    }
    
    r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
    if(r.text.find('Successfully Scheduled') != -1):
        print("Successfully Rescheduled")
        send("Successfully Rescheduled")
        EXIT = True
    else:
        print("ReScheduled Fail")
        send("ReScheduled Fail")


def is_logined():
    content = driver.page_source
    if(content.find("error") != -1):
        return False
    return True


def print_date(dates):
    for d in dates:
        print("%s \t business_day: %s" %(d.get('date'), d.get('business_day')))
    print()


last_seen = None
def get_available_date(dates):
    global last_seen

    def is_earlier(date):
        return datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d") > datetime.strptime(date, "%Y-%m-%d")

    for d in dates:
        date = d.get('date')
        if is_earlier(date) and date != last_seen:
            _, month, day = date.split('-')
            if(MY_CONDITION(month, day)):
                last_seen = date
                return date



if __name__ == "__main__":
    base_url = f'https://ais.usvisa-info.com/en-be/niv/schedule/{SCHEDULE}'

    # Checking for a rescheduled
    url = base_url + '/appointment'
    login(url)
    retry_count = 0
    while True:
        if retry_count > 6:
            break
        try:
            print(datetime.today())
            print("------------------")

            dates = get_date()[:5]
            print_date(dates)
            date = get_available_date(dates)
            if date:
                print(date)
                import json
                import pprint as pp
                # Send a message to Telegram
                print('Sending a test message.')
                response = send_message(f'NEW date found {date}')
                response_json = json.loads(response.text)
                assert response_json['ok']
                print('Results:')
                pp.pprint(response_json)

            if date:
                reschedule(date)

            if(EXIT):
                break

            time.sleep(SLEEP_TIME)
        except:
            retry_count += 1
            time.sleep(60*5)
    
    if(not EXIT):
        send("HELP! Crashed.")
