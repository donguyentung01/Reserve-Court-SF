from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys  
from selenium.webdriver.common.action_chains import ActionChains
from HELPER.messages import get_code
from datetime import datetime, timedelta
import sys  
import time as t
import requests
import json
import concurrent.futures
import pytz 

TIMEZONE = pytz.timezone("America/Los_Angeles") #all times are in San Francisco. 

def wait_for_target_time(target_timestamp, sleep_itvl=0.1):
    print(f"waiting for target time: {target_timestamp}")
    target_time = TIMEZONE.localize(datetime.strptime(target_timestamp, "%Y-%m-%d %H:%M:%S"))
    while datetime.now(TIMEZONE) < target_time:
        time_to_wait = (target_time - datetime.now(TIMEZONE)).total_seconds()
        if time_to_wait > 0:
            t.sleep(min(time_to_wait, sleep_itvl))  # Sleep in small increments

def spawn_driver(weblink): #create a web driver at the weblink provided 
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chromedriver_path = './chromedriver' 
    driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options) 
    driver.get(weblink)
    return driver 

def make_verification_request(verification_code, headers, url="https://api.rec.us/v1/users/mobile-totp/verify"): 
    print(f"sending back verification code {verification_code}")

    body = {
        "code": str(verification_code)
    }
    
    try:
        # Send the POST request with the body
        response = requests.post(url, headers=headers, data=json.dumps(body))
        
        if response.status_code == 200:
            return response.text # Assuming the response is in JSON format
        
        else:
            return f"Failed to make request. Status code: {response.status_code}. Response text: {response.text}"

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"
    
def make_reservation_request(headers, courtSportId, participantUserId, date, start_time, end_time, url="https://api.rec.us/v1/reservations"):
    # Define the body (data) for the POST request
    body = {
        "courtSportIds": [courtSportId],
        "from": {"date": date, "time": start_time},
        "participantUserId": participantUserId,
        "to": {"date": date, "time": end_time}
    }
    
    try:
        # Send the POST request with the body
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json() # Assuming the response is in JSON format
        
        else:
            return f"Failed to make request. Status code: {response.status_code}. Response text: {response.text}"
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

def get_access_token(driver):
    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie['name'] == 'access_token':
            access_token = cookie['value']
            return access_token
    return None 

def getHeaders(driver):
    access_token = get_access_token(driver)
    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Origin': 'https://www.rec.us',
            'Referer': 'https://www.rec.us/',
            "Content-Type": "application/json"
        }
        return headers 
    else:
        return None 

def make_send_verification_code_request(headers, url="https://api.rec.us/v1/users/mobile-totp/send"):
    print("requesting verification code") 
    # Define the body (data) for the POST request
    try:
        # Send the POST request with the body
        response = requests.post(url, headers=headers)
        
        if response.status_code == 200 or response.status_code == 201:
            return response.text # Assuming the response is in JSON format
        
        else:
            return f"Failed to make request. Status code: {response.status_code}. Response text: {response.text}"
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"
    
def make_payment_request(url, headers):
    # Define the body (data) for the POST request
    body = {
        "data": {}
    }

    try:
        # Send the POST request with the body
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json() # Assuming the response is in JSON format
        
        else:
            return f"Failed to make request. Status code: {response.status_code}. Response text: {response.text}"
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

def log_in(driver, email, password): 
    try:
        print("Logging in")
        login = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Log In')]")))
        login.click()

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )

        email_input = driver.find_element(By.NAME, "email")
        password_input = driver.find_element(By.NAME, "password")
    
        email_input.send_keys(email)  # Replace with your email
        password_input.send_keys(password)       # Replace with your password
    
        password_input.send_keys(Keys.RETURN)  # Alternatively, use .submit() on the form

    except Exception as e:
        print(f"Error: {e}")
        print("Error: Failed at login")
        sys.exit(1)

def get_court_href(driver, court):
    try:
        element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, f"//a[p[text()='{court}']]")
            )
        )

        href_link = element.get_attribute("href")

        return href_link
    except Exception as e:
        print(f"Error: {e}")
        print("Error: Failed at getting court href")
        sys.exit(1)

def make_get_court_info_request(url):
    response = requests.get(url)

# Check if the request was successful (status code 200)
    if response.status_code == 200:
    # Parse the JSON response
        data = response.json()
        return data
    else:
        print(f"Request failed with status code: {response.status_code}")
        return None 

def get_court_sport_id(response, sport_code):
    court_ids = []
    for court in response["location"]["courts"]:
        if court["sports"][0]["sportId"] == sport_code:
            court_ids.append(court["sports"][0]["id"])
    return court_ids

def make_user_profile_request(headers, url="https://api.rec.us/v1/users/household-members"):
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Request failed with status code: {response.status_code} and {response.json()}")
        return None 

def reserve_court_single_thread(court_id, user_id, date, start_time, end_time, headers, job_begin_time):
    response = make_reservation_request(headers, court_id, user_id, date, start_time, end_time)
    print(response)
    
    if "order" in response:
        order_id = response["order"]["id"]
        payment_status = make_payment_request(f"https://api.rec.us/v1/orders/{order_id}/pay", headers)
        
        if payment_status["data"]["status"] == "succeeded":
            print(f"Successfully reserved court {court_id} from {start_time} to {end_time}")
            job_end_time = t.time()
            print(f"Reservation job for court {court_id} took {job_end_time - job_begin_time} seconds.")
            return True
        
    return False
def book_court(court, date, sport, start_time, end_time, email, password, phone_number, is_multithreaded, target_time=f"{datetime.today().strftime('%Y-%m-%d')} 12:00:00"): 
    sports_URL_code = {
        "pickleball": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "tennis": "bd745b6e-1dd6-43e2-a69f-06f094808a96"
    }
    print(f"Spawning Chrome driver at https://www.rec.us/organizations/san-francisco-rec-park?tab=locations&date={date}&sports={sports_URL_code[sport]}")
    driver = spawn_driver(f"https://www.rec.us/organizations/san-francisco-rec-park?tab=locations&date={date}&sports={sports_URL_code[sport]}")

    log_in(driver, email, password)
    t.sleep(1)

    headers = getHeaders(driver) 

    court_info_api_endpoint = f"https://api.rec.us/v1/{get_court_href(driver, court)[19:]}"
    all_court_data = make_get_court_info_request(court_info_api_endpoint)
    all_court_ids = get_court_sport_id(all_court_data, sports_URL_code[sport])

    user_data = make_user_profile_request(headers)
    user_id = user_data[0]['id']

    preemptive_verification_code_target_time_obj = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=1)
    preemptive_verification_code_target_time = preemptive_verification_code_target_time_obj.strftime("%Y-%m-%d %H:%M:%S")

    wait_for_target_time(preemptive_verification_code_target_time) 

    print(make_send_verification_code_request(headers))
    verification_code = get_code(phone_number) 
    print(make_verification_request(verification_code, headers))
    
    wait_for_target_time(target_time)    

    job_begin_time = t.time()
    
    if is_multithreaded:
        print("Running reservation program on multi-threads (1 thread per court)")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for court_id in all_court_ids:
                futures.append(executor.submit(reserve_court_single_thread, court_id, user_id, date, start_time, end_time, headers, job_begin_time))

            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(futures):
                if future.result():  # If reservation was successful
                    driver.quit()
                    sys.exit(0)
    else:
        print("Running reservation program on one single thread")
        for court_id in all_court_ids:
            response = make_reservation_request(headers, court_id, user_id, date, start_time, end_time)
            if "order" in response: 
                order_id = response["order"]["id"]
                payment_status = make_payment_request(f"https://api.rec.us/v1/orders/{order_id}/pay", headers)
                if payment_status["data"]["status"] == "succeeded":
                    print(f"Successfully reserve court {court} from {start_time} to {end_time}")
                    job_end_time = t.time()
                    print(f"Reservation job takes {job_end_time - job_begin_time} seconds.")
                    sys.exit(0)

    print(f"Couldn't reserve the court")
    driver.quit()
