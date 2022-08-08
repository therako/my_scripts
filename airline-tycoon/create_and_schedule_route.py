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
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options

from route import (
    extract_route_price_stats,
    find_hub_id,
    is_extracted,
    login,
    select_route,
)
from seat import find_seat_config


chrome_options = Options()
chrome_options.add_argument("--window-size=1920x1080")


def open_route(driver: WebDriver, hub: str, destination: str, hub_id: int):
    if not hub_id:
        raise Exception("Unknown hub")

    driver.get(
        f"http://tycoon.airlines-manager.com/network/newlinefinalize/{hub_id}/{destination.lower()}"
    )

    driver.find_element(By.XPATH, '//*[@id="linePurchaseForm"]/input').submit()


def get_aircraft_config(seat_config_df: pd.DataFrame, nth=2):
    return (
        seat_config_df.sort_values(by="total_turnover", ascending=False)
        .reset_index()
        .loc[nth - 1]
    )


def select_flight(driver: WebDriver, hub_id: int, aircraft_model: str):
    time.sleep(1)
    js_click(driver, driver.find_element(By.XPATH, f"//span[@data-hubid='{hub_id}']"))
    time.sleep(2)
    el = driver.find_element("id", "aircraftNameFilter")
    el.clear()
    el.send_keys(searchable_aircraft_model(aircraft_model))
    time.sleep(2)
    js_click(
        driver,
        driver.find_element(
            By.CSS_SELECTOR, "input[type='radio'][value='utilizationPercentageAsc']"
        ),
    )


@retry(NoSuchElementException, delay=1, tries=10, jitter=1)
def select_route_for_aircraft(driver: WebDriver, hub: str, destination: str):
    js_click(
        driver,
        driver.find_element(
            By.XPATH, f"//span[contains(text(), '{hub} / {destination}')]"
        ),
    )


def searchable_aircraft_model(raw: str):
    return raw.replace("Ił-", "")


def assign_flights(
    driver: WebDriver,
    hub_id: int,
    hub: str,
    destination: str,
    seat_config: pd.Series,
    aircraft_model: str,
    assigned_aircrafts: int,
):
    print(f"Configuring with:\n{seat_config}")
    print(
        f"Excluding already configured {assigned_aircrafts}, scheduing {seat_config['no'] - assigned_aircrafts} flights"
    )
    for i in range(0, seat_config["no"] - assigned_aircrafts):
        print(f"Scheduling flight {i+1}...")
        schedule_a_flight(driver, hub_id, hub, destination, aircraft_model)


def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)


def schedule_a_flight(driver: WebDriver, hub_id, hub, destination, aircraft_model):
    driver.get("http://tycoon.airlines-manager.com/network/planning")
    select_flight(driver, hub_id, aircraft_model)
    check_for_free_aircraft(driver, hub, aircraft_model)
    select_route_for_aircraft(driver, hub, destination)

    js_click(
        driver,
        driver.find_element(
            By.XPATH, '//table[@class="planningArea"]/tbody/tr[2]/td[3]'
        ),
    )
    js_click(
        driver,
        driver.find_element(
            By.XPATH, '//div[@id="planning"]/table[1]/tbody/tr[2]/td[1]/img'
        ),
    )
    js_click(driver, driver.find_element("id", "planningSubmit"))


def check_for_free_aircraft(driver: WebDriver, hub, aircraft_model):
    time.sleep(1)
    try:
        use = driver.find_element(
            By.XPATH, "//*[@class='aircraftsBox']/div[1]/div[2]/span[1]/b"
        )
        if use.text != "0%":
            raise Exception(f"No free flights in HUB {hub} of type {aircraft_model}")
    except NoSuchElementException:
        raise Exception(f"No flights in HUB {hub} of type {aircraft_model}")


def saved_seat_config_df(
    hub: str,
    destination: str,
    aircraft_maker: str,
    aircraft_model: str,
) -> pd.DataFrame:
    if os.path.exists(
        seat_config_file(hub, destination, aircraft_maker, aircraft_model)
    ):
        return pd.read_csv(
            seat_config_file(hub, destination, aircraft_maker, aircraft_model)
        )

    return pd.DataFrame()


def save_seat_config_df(
    df: pd.DataFrame,
    hub: str,
    destination: str,
    aircraft_maker: str,
    aircraft_model: str,
):
    df.to_csv(seat_config_file(hub, destination, aircraft_maker, aircraft_model))


def seat_config_file(
    hub: str,
    destination: str,
    aircraft_maker: str,
    aircraft_model: str,
):
    return f"tmp/seat/{hub}_{destination}_{aircraft_maker}_{aircraft_model}.csv"


@retry(NoSuchElementException, delay=5, tries=6)
def find_assigned_flight_count(driver, hub, destination):
    select_route(driver, f"{hub} - {destination}")
    return int(
        driver.find_element(
            By.XPATH, '//div[@id="showLine"]/div[3]/ul[1]/li[2]/strong'
        ).text
    )


def clear_all_and_enter(inputs: List[Tuple[WebElement, Any]]):
    for set in inputs:
        set[0].clear()
        set[0].send_keys("0")
    time.sleep(2)
    for set in inputs:
        set[0].clear()
        set[0].send_keys(str(set[1]))
        time.sleep(2)


def reconfigure_flight_seats(
    driver: WebDriver,
    hub: str,
    destination: str,
    seat_config: pd.Series,
):
    select_route(driver, f"{hub} - {destination}")
    aircrafts = driver.find_elements(By.XPATH, '//div[@class="aircraftListView"]/div')
    aircraft_links = []
    for aircraft in aircrafts:
        aircraft_links.append(
            aircraft.find_element(By.LINK_TEXT, "Aircraft details").get_attribute(
                "href"
            )
        )

    for i, aircraft_link in enumerate(aircraft_links):
        print(f"Reconfiguring seat on Aircraft {i+1}")
        driver.get(aircraft_link + "/reconfigure")
        clear_all_and_enter(
            [
                (driver.find_element("id", "ecoManualInput"), seat_config["economy"]),
                (driver.find_element("id", "busManualInput"), seat_config["business"]),
                (driver.find_element("id", "firstManualInput"), seat_config["first"]),
                (driver.find_element("id", "cargoManualInput"), seat_config["cargo"]),
                (
                    driver.find_element("id", "aircraft_name"),
                    f"{hub}-{destination}-{i}",
                ),
            ]
        )
        driver.find_element(
            By.XPATH, '//input[@value="Confirm the reconfiguration"]'
        ).submit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "hub", help="Enter HUB name you need to extract route stats for"
    )
    parser.add_argument(
        "destinations",
        help="List of destination airport code. eg: BFN,TGV,CPT",
    )
    parser.add_argument(
        "--aircraft_make",
        "-m",
        help="Aircraft maker name as per Airline Tycoon eg., Ilyushin (Default: Boeing)",
        default="Boeing",
    )
    parser.add_argument(
        "--aircraft_model",
        "-a",
        help="Aircraft model name for the Aircraft maker eg., 96-300 (Default: 747-400)",
        default="747-400",
    )
    parser.add_argument(
        "--nth_best_config",
        "-n",
        type=int,
        help="Configure with the nth best seat config based on turnover (Default: 2)",
        default=2,
    )
    parser.add_argument(
        "--no_headless",
        "-nh",
        action="store_true",
        help="Disable headless and show browser",
    )
    args = parser.parse_args()
    try:
        if not args.no_headless:
            chrome_options.add_argument("--headless")

        driver = webdriver.Chrome(options=chrome_options)
        login(driver)
        hub_id = find_hub_id(driver, args.hub)

        for destination in args.destinations.split(","):
            print(f"Working on route {args.hub} - {destination}")
            if not is_extracted(args.hub, destination):
                open_route(driver, args.hub, destination, hub_id)
                extract_route_price_stats(driver, args.hub, destination)

            seat_config_df = saved_seat_config_df(
                args.hub, destination, args.aircraft_make, args.aircraft_model
            )
            if seat_config_df.empty:
                seat_config_df = find_seat_config(
                    driver,
                    args.hub,
                    [destination],
                    args.aircraft_make,
                    args.aircraft_model,
                    no_negative=True,
                )
                save_seat_config_df(
                    seat_config_df,
                    args.hub,
                    destination,
                    args.aircraft_make,
                    args.aircraft_model,
                )

            assigned_aircrafts = find_assigned_flight_count(
                driver, args.hub, destination
            )
            config = get_aircraft_config(seat_config_df, nth=args.nth_best_config)
            assign_flights(
                driver,
                hub_id,
                args.hub,
                destination,
                config,
                args.aircraft_model,
                assigned_aircrafts,
            )

            reconfigure_flight_seats(driver, args.hub, destination, config)
    except Exception:
        traceback.print_exception(*sys.exc_info())
    finally:
        driver.quit()
        print("Done")
