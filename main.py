from cryptography.fernet import Fernet

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json, time, argparse, os, sys

dirname = os.path.dirname(__file__)

# Set up argument parsing
parser = argparse.ArgumentParser(add_help=False)

def __run_daily_health_check(username, password):
    """Performs the daily health check"""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        browser = webdriver.Chrome(options=chrome_options)
        browser.get("https://yalesurvey.ca1.qualtrics.com/jfe/form/SV_eFnltn7gS5xctc9?Type=checkin")

        # Yale NetID login page
        browser.find_element_by_id('username').send_keys(username)
        browser.find_element_by_id('password').send_keys(password)
        browser.find_element_by_xpath('//*[@id="fm1"]/fieldset/input[4]').click()

        # Yale OAUTH page
        if __element_on_page(browser, 'duo_iframe'):
            browser.switch_to.frame(browser.find_element_by_id('duo_iframe'))
            browser.find_element_by_xpath('//*[@id="auth_methods"]/fieldset[1]/div[1]/button').click()
            browser.switch_to.default_content()

        # We need to wait for the user to respond with CAS
        element = WebDriverWait(browser, 63).until(EC.presence_of_element_located((By.ID, 'QID1-3-label')))
        element.click()
        browser.find_element_by_id('NextButton').click()
        covidbutton = WebDriverWait(browser, 3).until(EC.presence_of_element_located((By.ID, 'QID19-2-label')))
        covidbutton.click()
        browser.find_element_by_id('NextButton').click()

        return True
    except:
        e = sys.exc_info()[0]
        print(e)
        return False
    finally:
        browser.quit()


def __element_on_page(browser, id):
    """Checks if element is on page"""
    try:
        frame = browser.find_element_by_id(id)
    except NoSuchElementException:
        return False
    return True


# ==== RUNNABLE FUNCTIONS ====


# add-user command, which adds a user to the list of health checks
commands = parser.add_subparsers(title="command", dest="command")
subparser1 = commands.add_parser("add-user", description="Add a user to the YailyHealthCheck list.")
subparser1.add_argument("--name", help="User's full name", required=True)
subparser1.add_argument("--username", help="User's Yale NetID", required=True)
subparser1.add_argument("--password", help="User's Yale NetID password", required=True)

def add_user(name, username, password):
    """Adds a user to the health check list"""
    with open(os.path.join(dirname, 'vault.json'), 'r+') as json_file:
        data = json.load(json_file)
        data['users'].append({
            'name': name,
            'username': username,
            'password': Fernet(data['key'].encode()).encrypt(password.encode()).decode()
        })
        json_file.seek(0)
        json.dump(data, json_file, indent=4)
        json_file.truncate()
        print('Added user "', username, '" to YailyHealthCheck automation list.')

# Add run as a command
subparser2 = commands.add_parser("run", description="Run the YailyHealthCheck list.")
subparser2.add_argument("--index", help="Index of user to run for, if applicable", required=False, default=None, type=int)

def run(index):
    """Runs the application workflow, or for a specified user only"""
    with open(os.path.join(dirname, 'vault.json'), 'r') as json_file:
        data = json.load(json_file)
        key = data['key'].encode()
        userlist = data['users'] if index == None else [data['users'][index]]
        for user in userlist:
            username = user['username']
            password = Fernet(key).decrypt(user['password'].encode()).decode()
            print('\nPerforming daily health check for user:', user["name"])
            if __run_daily_health_check(username, password):
                print('Success!')
            else:
                print('Failed.')
        print('')


# ==== EXECUTION DESK ====

def execute():
    args = parser.parse_args()
    if args.command == 'add-user':
        add_user(args.name, args.username, args.password)
    elif args.command == 'run':
        run(args.index)
execute()