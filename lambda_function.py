import os
import time
import logging
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import traceback

parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
parser.add_argument('--local', action='store_true', help='Run in local mode')
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_parameters():
    return {
        'ITSLEARNING_USERNAME': os.environ.get('ITSLEARNING_USERNAME'),
        'ITSLEARNING_PASSWORD': os.environ.get('ITSLEARNING_PASSWORD'),
        'SMTP_SERVER': os.environ.get('SMTP_SERVER'),
        'SMTP_PORT': os.environ.get('SMTP_PORT'),
        'SMTP_USERNAME': os.environ.get('SMTP_USERNAME'),
        'SMTP_PASSWORD': os.environ.get('SMTP_PASSWORD'),
        'EMAIL_FROM': os.environ.get('EMAIL_FROM'),
        'EMAIL_TO': os.environ.get('EMAIL_TO')
    }

def get_driver(is_local=False, max_retries=5, retry_interval=5):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    if is_local:
        service = Service('/usr/local/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        selenium_host = os.environ.get('SELENIUM_HOST', 'localhost')
    
        for attempt in range(max_retries):
            try:
                driver = webdriver.Remote(
                    command_executor=f'http://{selenium_host}:4444/wd/hub',
                    options=chrome_options
                )
                driver.implicitly_wait(10)
                return driver
            except WebDriverException as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed. Retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)
                else:
                    logging.error(f"Failed to connect to Selenium after {max_retries} attempts.")
                    raise
    
    driver.implicitly_wait(10)
    return driver

def is_element_present(driver, by, value):
    """Checks if an element is present in the current html"""
    try:
        driver.find_element(by, value)
        return True
    except NoSuchElementException:
        return False

def check_for_js_errors(driver):
    logs = driver.get_log('browser')
    for log in logs:
        if log['level'] == 'SEVERE':
            logging.error(f"JavaScript error: {log['message']}")

def login(driver, username, password):
    driver.get("https://cloud.schule-mv.de/univention/saml/?location=/univention/portal/")
    time.sleep(15)  # Increased initial wait time
    logging.info("Navigated to login page")

    try:
        username_field = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, "umcLoginUsername"))
        )
        logging.debug("The login form is present.")
        username_field.send_keys(username)
        logging.debug("Username has been entered")

        password_field = driver.find_element(By.ID, "umcLoginPassword")
        password_field.send_keys(password)
        logging.debug("Password has been entered")

        # Try multiple locators for the login button
        button_locators = [
            (By.XPATH, "//button[contains(@class, 'umcLoginFormButton') and .//span[contains(text(), 'Anmelden')]]"),
            (By.XPATH, "//button[@type='submit' and contains(@class, 'umcLoginFormButton')]"),
            (By.CSS_SELECTOR, "button.umcLoginFormButton[type='submit']")
        ]

        login_button = None
        for locator in button_locators:
            try:
                login_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable(locator)
                )
                if login_button:
                    break
            except TimeoutException:
                continue

        if not login_button:
            raise Exception("Login button not found with any of the specified locators")

        logging.debug(f"Login button found: {login_button.is_displayed()}, {login_button.is_enabled()}")
        logging.debug(f"Login button HTML: {login_button.get_attribute('outerHTML')}")

        # Try multiple methods to click the button
        try:
            login_button.click()
        except Exception as e:
            logging.debug(f"Standard click failed: {str(e)}. Trying JavaScript click.")
            driver.execute_script("arguments[0].click();", login_button)

        logging.debug("The login button has been clicked")

        time.sleep(5) 
        check_for_js_errors(driver)


        itslearning_link = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'itslearning') and contains(@class, 'portal-tile')]"))
        )
        logging.debug("itslearning link is present")

        itslearning_url = itslearning_link.get_attribute('href')
        logging.debug(f"itslearning URL: {itslearning_url}")

        logging.debug("Trying to open itslearning URL")
        driver.execute_script(f"window.open('{itslearning_url}', '_blank');")
        
        # Warten Sie kurz, um sicherzustellen, dass der neue Tab geöffnet wurde
        time.sleep(2)

        # Wechseln Sie zum neuen Tab
        driver.switch_to.window(driver.window_handles[-1])
        
        logging.debug(f"Current url after tab switch: {driver.current_url}")
        
        logging.info("Login and navigation to itslearning successful")

    except Exception as e:
        logging.error(f"Error during itslearning navigation: {str(e)}")
        logging.debug(f"Current URL: {driver.current_url}")
        logging.debug(f"Current page source: {driver.page_source}")
        raise
       


def get_messages(driver):
    messages = []
    try:
        logging.debug("Trying to click on the messaging button")
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, "im2-open-button"))
        )
        
        im_button = driver.find_element(By.ID, "im2-open-button")
        
        actions = ActionChains(driver)
        actions.move_to_element(im_button).click().perform()
        
        logging.debug("Waiting for the message overlay to appear")
        WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.ID, "im2-overlay-wrapper"))
        )
        
        # Kurze Pause, um sicherzustellen, dass das Overlay vollständig geladen ist
        time.sleep(2)
        
        logging.debug("Scrolling the message overlay")
        overlay = driver.find_element(By.ID, "im2-overlay-wrapper")
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", overlay)
        
        # Weitere kurze Pause nach dem Scrollen
        time.sleep(2)
        
        logging.debug("Trying to locate message threads")
        threads = WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "itsl-im2-thread"))
        )
        
        logging.info(f"Found {len(threads)} message threads")
        
        for thread in threads:
            if is_element_present(thread, By.CLASS_NAME, "itsl-im2-thread__title"):
                title = thread.find_element(By.CLASS_NAME, "itsl-im2-thread__title").text
                timestamp = thread.find_element(By.CLASS_NAME, "itsl-im2-thread__timestamp").text
                message = thread.find_element(By.CLASS_NAME, "itsl-im2-thread__text").text
                messages.append([title, timestamp, message])
                logging.debug(f"Extracted message: {title[:20]}...")
            else:
                logging.warning("Thread element structure not as expected")
        
    except Exception as e:
        logging.error(f"Error while fetching messages: {str(e)}")
        logging.error(f"Current URL: {driver.current_url}")
        logging.error(f"Page source: {driver.page_source}")
    
    return messages

def get_notifications(driver):
    notifications = []
    try:
        logging.debug("Clicking on notification button")
        notification_button = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.ID, "Notification"))
        )
        driver.execute_script("arguments[0].click();", notification_button)

        WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.ID, "notifications-overlay-wrapper"))
        )
        logging.debug("Notifications' wrapper is visible")
        time.sleep(10)

        notifications_list = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "itsl-personal-notifications__list"))
        )
        logging.debug("Notifications are visible")
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", notifications_list)

        time.sleep(10)

        notifications_elements = notifications_list.find_elements(By.TAG_NAME, "li")
        logging.debug(f'There are {len(notifications_elements)} notifications')
        for notification in notifications_elements:
            if is_element_present(notification, By.CLASS_NAME, "itsl-personal-notification__item__title"):
                title_element = notification.find_element(By.CLASS_NAME, "itsl-personal-notification__item__title")
                title = title_element.text
                link = title_element.get_attribute("href")
                info_element = notification.find_element(By.CLASS_NAME, "itsl-personal-notification__item__info")
                info = info_element.text
                
                notifications.append([title, link, info])
            else:
                logging.warning("Notification element structure not as expected")

    except Exception as e:
        logging.error(f"Error while fetching notifications: {str(e)}")
        logging.error(f"Current URL: {driver.current_url}")
        logging.error(f"Page source: {driver.page_source}")
        logging.error(f"Stacktrace: {traceback.format_exc()}")

    return notifications


def check_for_recent_notifications(notifications):
    """Check if notification is recent.
    
    Recent notificaations contain either yesterdays day string or 'Vor' with h or min.
    """
    yesterday = datetime.today() - timedelta(days=1)
    weekday_index = yesterday.date().weekday() # to get German Weeday out of list
    weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    yesterday_str = weekdays[weekday_index]

    recent_notification = False
    for notification in notifications:
        time_text = notification[2]
        if (yesterday_str in time_text) or ("Vor" in time_text):
            recent_notification = True
    return recent_notification

def check_for_recent_messages(messages):
    """Check if message is recent.
    
    Recent messages contain mm.dd of todays or yesterdays date. There is no year given.
    As messages are frequent, only check the first 5 or so in order not to see last years.
    """
    today_str_part = datetime.today().strftime("%d.%m")
    yesterday_str_part = (datetime.today()-timedelta(days=1)).strftime("%d.%m")
    recent_messages = False
    for message in messages[:5]:
        message_date_str = message[1][:5]
        if message_date_str == today_str_part or message_date_str == yesterday_str_part:
            recent_messages = True
    return recent_messages

def send_email(betreff, messages, notifications, params):
    smtp_server = params['SMTP_SERVER']
    smtp_port = params['SMTP_PORT']
    smtp_username = params['SMTP_USERNAME']
    smtp_password = params['SMTP_PASSWORD']
    email_from = params['EMAIL_FROM']
    email_to = params['EMAIL_TO'].split(', ')

    msg = MIMEMultipart()
    msg['From'] = email_from
    msg['To'] = ', '.join(email_to)
    msg['Subject'] = betreff

    body = "Es gibt neue Mitteilungen oder Benachrichtigungen:\n\n"

    if messages:
        logging.debug("Messages have been added to the email.")
        body += "Mitteilungen:\n"
        for message in messages:
            body += f"Von: {message[0]}\n"
            body += f"Zeitstempel: {message[1]}\n"
            body += f"Inhalt: {message[2]}\n\n"

    if notifications:
        logging.debug("Notifications have been added to the email.")
        body += "Benachrichtigungen:\n"
        for notification in notifications:
            body += f"Titel: {notification[0]}\n"
            body += f"Link: {notification[1]}\n"
            body += f"Info: {notification[2]}\n\n"

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_username, smtp_password)
    text = msg.as_string()
    server.sendmail(email_from, email_to, text)
    logging.debug("Email(s) have been sent.")
    server.quit()

def lambda_handler(event, context):
    params = get_parameters()
    driver = None
    try:
        driver = get_driver(is_local=args.local)
        logging.info("WebDriver initialized successfully")

        login(driver, params['ITSLEARNING_USERNAME'], params['ITSLEARNING_PASSWORD'])
        logging.info("Login successful")

        check_for_js_errors(driver)
        messages = get_messages(driver)
        logging.info(f"Retrieved {len(messages)} messages")

        check_for_js_errors(driver)
        notifications = get_notifications(driver)
        logging.info(f"Retrieved {len(notifications)} notifications")

        check_for_js_errors(driver)

        recent_messages = check_for_recent_messages(messages)
        recent_notifications = check_for_recent_notifications(notifications)

        betreff = "Es gibt weder neue Mitteilungen noch neue Benachrichtigungen"
        if recent_messages or recent_notifications:
            betreff = "Es gibt neue Mitteilungen oder Benachrichtigungen"

        send_email(betreff, messages[:5], notifications[:5], params)
        logging.info("Email sent successfully")

        return {
            'statusCode': 200,
            'body': 'Scraping und E-Mail-Versand erfolgreich abgeschlossen.'
        }

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        logging.error(f"Stacktrace: {traceback.format_exc()}")
        if driver:
            logging.error(f"Final URL: {driver.current_url}")
            logging.error(f"Final page source: {driver.page_source}")
        return {
            'statusCode': 500,
            'body': f'An error occurred: {str(e)}'
        }

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    print(lambda_handler(None, None))