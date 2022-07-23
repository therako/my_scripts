import argparse
import os
import sys
import time
import traceback
from typing import Any, List, Tuple

import pandas as pd
from retry import retry
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from route import login
from seat import js_click

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920x1080")


def buy_aircraft(
    driver, hub: str, aircraft_make: str, aircraft_model: str, number: int
):
    driver.get(
        f"https://tycoon.airlines-manager.com/aircraft/buy/new/{aircraft_make.lower()}"
    )

    aircraft_list = driver.find_elements(By.XPATH, '//div[@class="aircraftList"]/div')
    for aircraft in aircraft_list:
        if (
            f"{aircraft_model.lower()} / {aircraft_make.lower()}"
            in aircraft.find_element(By.CLASS_NAME, "title").text.lower()
        ):
            js_click(
                driver,
                aircraft.find_element(By.XPATH, "form/div[1]/div[3]/div/span[1]/img"),
            )
            el = aircraft.find_element(
                By.XPATH, "form/div[1]/div[3]/div/span[2]/input[1]"
            )
            el.clear()
            el.send_keys(str(number))
            el.send_keys(Keys.ENTER)

            aircraft_hub = Select(driver.find_element("id", "aircraft_hub"))
            for option in aircraft_hub.options:
                if hub.lower() in option.text.lower():
                    option.click()

            js_click(
                driver,
                driver.find_element(
                    By.XPATH,
                    '//*[@id="aircraft_buyNew_step3"]/div/div[2]/div[10]/div[2]/input',
                ),
            )
            print(f"Bought {number} of {aircraft_model} to HUB {hub}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "hub", help="Enter HUB name you need to extract route stats for"
    )
    parser.add_argument(
        "--aircraft_make",
        "-m",
        help="Aircraft maker name as per Airline Tycoon (Default: Boeing)",
        default="Boeing",
    )
    parser.add_argument(
        "--aircraft_model",
        "-a",
        help="Aircraft model name for the Aircraft maker (Default: 747-400)",
        default="747-400",
    )
    parser.add_argument(
        "--number",
        "-n",
        type=int,
        help="No. of flights to buy (Default: 30)",
        default=30,
    )
    args = parser.parse_args()
    try:
        driver = webdriver.Chrome(options=chrome_options)
        login(driver)
        buy_aircraft(
            driver, args.hub, args.aircraft_make, args.aircraft_model, args.number
        )
    except Exception:
        traceback.print_exception(*sys.exc_info())
    finally:
        driver.quit()
