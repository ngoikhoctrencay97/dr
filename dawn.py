import ast
import json
import re
import requests
import random
import time
import datetime
import urllib3
from PIL import Image
import base64
from io import BytesIO
import ddddocr
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from loguru import logger

KeepAliveURL = "https://www.aeropres.in/chromeapi/dawn/v1/userreward/keepalive"
GetPointURL = "https://www.aeropres.in/api/atom/v1/userreferral/getpoint"
LoginURL = "https://www.aeropres.in//chromeapi/dawn/v1/user/login/v2"
PuzzleID = "https://www.aeropres.in/chromeapi/dawn/v1/puzzle/get-puzzle"

# Create a request session
session = requests.Session()

# Set common request headers
headers = {
    "Content-Type": "application/json",
    "Origin": "chrome-extension://fpdkjdnhkakefebpekbdhillbhonfjjp",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Priority": "u=1, i",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
}


def GetPuzzleID():
    r = session.get(PuzzleID, headers=headers, verify=False).json()
    puzzid = r['puzzle_id']
    return puzzid

# Check captcha expression
def IsValidExpression(expression):
    # Check if the expression is a 6-character alphanumeric string
    pattern = r'^[A-Za-z0-9]{6}$'
    if re.match(pattern, expression):
        return True
    return False

# Captcha recognition
def RemixCaptacha(base64_image):
    # Decode Base64 string into binary data
    image_data = base64.b64decode(base64_image)
    # Use BytesIO to convert binary data into a readable file object
    image = Image.open(BytesIO(image_data))
    #####################################
    # Convert the image to RGB mode (if not already)
    image = image.convert('RGB')
    # Create a new image (white background)
    new_image = Image.new('RGB', image.size, 'white')
    # Get the width and height of the image
    width, height = image.size
    # Iterate through all pixels
    for x in range(width):
        for y in range(height):
            pixel = image.getpixel((x, y))
            # If the pixel is black, retain it; otherwise, set it to white
            if pixel == (48, 48, 48):  # Black pixel
                new_image.putpixel((x, y), pixel)  # Keep original black
            else:
                new_image.putpixel((x, y), (255, 255, 255))  # Replace with white

    ##################

    # Create an OCR object
    ocr = ddddocr.DdddOcr(show_ad=False)
    ocr.set_ranges(0)
    result = ocr.classification(new_image)
    logger.debug(f'[1] Captcha recognition result: {result}, is it a valid captcha {IsValidExpression(result)}')
    if IsValidExpression(result) == True:
        #rc = eval(result)
        return result


def login(USERNAME, PASSWORD):
    puzzid = GetPuzzleID()
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")
    data = {
        "username": USERNAME,
        "password": PASSWORD,
        "logindata": {
            "_v": "1.0.7",
            "datetime": current_time
        },
        "puzzle_id": puzzid,
        "ans": "0"
    }
    # Captcha recognition part
    refresh_image = session.get(f'https://www.aeropres.in/chromeapi/dawn/v1/puzzle/get-puzzle-image?puzzle_id={puzzid}', headers=headers, verify=False).json()
    code = RemixCaptacha(refresh_image['imgBase64'])
    if code:
        logger.success(f'[√] Successfully retrieved captcha result {code}')
        data['ans'] = str(code)
        login_data = json.dumps(data)
        logger.info(f'[2] Login data: {login_data}')
        try:
            r = session.post(LoginURL, login_data, headers=headers, verify=False).json()
            logger.debug(r)
            token = r['data']['token']
            logger.success(f'[√] Successfully obtained AuthToken {token}')
            return token
        except Exception as e:
            logger.error(f'[x] Captcha error, trying to retrieve again...')

def KeepAlive(USERNAME, TOKEN):
    data = {"username": USERNAME, "extensionid": "fpdkjdnhkakefebpekbdhillbhonfjjp", "numberoftabs": 0, "_v": "1.0.7"}
    json_data = json.dumps(data)
    headers['authorization'] = "Berear " + str(TOKEN)
    r = session.post(KeepAliveURL, data=json_data, headers=headers, verify=False).json()
    logger.info(f'[3] Keeping connection alive... {r}')


def GetPoint(TOKEN):
    headers['authorization'] = "Berear " + str(TOKEN)
    r = session.get(GetPointURL, headers=headers, verify=False).json()
    logger.success(f'[√] Successfully retrieved points {r}')


def main(USERNAME, PASSWORD):
    TOKEN = ''
    if TOKEN == '':
        while True:
            TOKEN = login(USERNAME, PASSWORD)
            if TOKEN:
                break
    # Initialize counter
    count = 0
    max_count = 200  # Re-authenticate after 200 runs
    while True:
        try:
            # Perform KeepAlive and GetPoint operations
            KeepAlive(USERNAME, TOKEN)
            GetPoint(TOKEN)
            # Update counter
            count += 1
            # Re-authenticate after reaching max_count
            if count >= max_count:
                logger.debug(f'[√] Re-authenticating to get new Token...')
                while True:
                    TOKEN = login(USERNAME, PASSWORD)
                    if TOKEN:
                        break
                count = 0  # Reset counter
        except Exception as e:
            logger.error(e)


if __name__ == '__main__':
    with open('password.txt', 'r') as f:
        username, password = f.readline().strip().split(':')
    main(username, password)
