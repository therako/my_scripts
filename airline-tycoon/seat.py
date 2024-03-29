import argparse
import os
import sys
import time
import traceback
from dataclasses import dataclass
from typing import List

import pandas as pd
from retry import retry
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from route import RouteStats, non_decimal


@dataclass
class WaveStat:
    no: int
    economy: int
    business: int
    first: int
    cargo: int

    turnover_per_wave: float
    roi: float
    total_turnover: float
    turnover_days: int
    max_configured: str


def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)


def clear_previous_configs(driver):
    rows = driver.find_elements(
        By.XPATH, '//*[@id="nwy_seatconfigurator_circuitinfo"]/table/tbody/tr'
    )
    for row in rows:
        try:
            row.find_element(By.XPATH, "td[10]/input").click()
        except NoSuchElementException:
            pass


def find_seat_config(
    driver: webdriver.Remote,
    source: str,
    destinations: List[str],
    aircraft_make: str,
    aircraft_model: str,
    no_negative=False,
) -> pd.DataFrame:
    driver.get("https://destinations.noway.info/en/seatconfigurator/index.html")
    clear_previous_configs(driver)
    cf_aircraftmake = Select(driver.find_element("id", "cf_aircraftmake"))
    for option in cf_aircraftmake.options:
        if aircraft_make.lower() in option.text.lower():
            option.click()

    cf_aircraftmodel = Select(driver.find_element("id", "cf_aircraftmodel"))
    for option in cf_aircraftmodel.options:
        if f"{aircraft_model.lower()} (" in option.text.lower():
            option.click()

    change_to_airport_codes(driver)

    for destination in destinations:
        fillin_route_stats(driver, source, destination)

    time.sleep(5)
    calculate_seat_config(driver, no_negative)
    wave_stats = scan_seat_configs(driver)
    clear_previous_configs(driver)
    return seat_configs_df(wave_stats)


def seat_configs_df(wave_stats) -> pd.DataFrame:
    df = pd.DataFrame(wave_stats)
    df["total_turnover"] = pd.to_numeric(df["total_turnover"], downcast="integer")
    df["turnover_per_wave"] = pd.to_numeric(df["turnover_per_wave"], downcast="integer")
    df.loc[:, "total_turnover_str"] = df["total_turnover"].map("{:,}".format)
    df["note"] = ""
    df.iloc[df["roi"].idxmax(), df.columns.get_loc("note")] = "Best ROI"
    df.iloc[df["total_turnover"].idxmax(), df.columns.get_loc("note")] = "Best Turnover"
    print(df)
    return df


@retry((NoSuchElementException, ElementClickInterceptedException), delay=5, tries=6)
def calculate_seat_config(driver, no_negative=False):
    if no_negative:
        js_click(driver, driver.find_element("id", "nonegativeconfig"))

    js_click(driver, driver.find_element("id", "calculate_button"))


@retry(ElementClickInterceptedException, delay=5, tries=6)
def change_to_airport_codes(driver):
    try:
        for el in driver.find_elements(By.LINK_TEXT, "Quick Entry"):
            el.click()
    except NoSuchElementException:
        pass


def fillin_route_stats(driver, source: str, destination: str):
    cf_hub_src = driver.find_element("id", "cf_hub_src")
    cf_hub_src.send_keys(source)
    cf_hub_dst = driver.find_element("id", "cf_hub_dst")
    cf_hub_dst.send_keys(destination)

    route_stats: RouteStats = read_route_stats(source, destination)
    form_map = {
        "auditprice_eco": route_stats.economy.price,
        "auditprice_bus": route_stats.business.price,
        "auditprice_first": route_stats.first.price,
        "auditprice_cargo": route_stats.cargo.price,
        "demand_eco": route_stats.economy.demand,
        "demand_bus": route_stats.business.demand,
        "demand_first": route_stats.first.demand,
        "demand_cargo": route_stats.cargo.demand,
    }
    for k, v in form_map.items():
        driver.find_element("id", k).send_keys(v)

    add_to_circuit(driver)


@retry(ElementClickInterceptedException, delay=5, tries=6)
def add_to_circuit(driver):
    js_click(driver, driver.find_element("id", "add2circuit_button"))


def scan_seat_configs(driver, maxWave=10):
    wave_stats = []
    for wave in range(1, maxWave):
        if wave != 1:
            if not select_wave(driver, wave):
                break

        wave_stats.append(extract_wave_config(driver, wave))

    return wave_stats


@retry(NoSuchElementException, delay=5, tries=6)
def extract_wave_config(driver, wave: int):
    wave_stat_el = driver.find_element("id", f"nwy_seatconfigurator_wave_{wave}_stats")
    seat_config_el = wave_stat_el.find_elements(
        By.XPATH,
        "table[1]/tbody/tr[3]/td",
    )
    total_seat_config_el = wave_stat_el.find_elements(
        By.XPATH,
        "table[1]/tbody/tr[4]/td",
    )

    return WaveStat(
        no=wave,
        economy=int(seat_config_el[1].text),
        business=int(seat_config_el[2].text),
        first=int(seat_config_el[3].text),
        cargo=int(seat_config_el[4].text),
        turnover_per_wave=decodeCost(seat_config_el[5].text),
        roi=float(non_decimal.sub("", seat_config_el[6].text)),
        total_turnover=decodeCost(total_seat_config_el[5].text),
        turnover_days=int(non_decimal.sub("", total_seat_config_el[6].text)),
        max_configured=wave_stat_el.find_element(
            By.XPATH, "table[2]/tbody/tr[3]/td[9]"
        ).text,
    )


def decodeCost(costStr: str) -> float:
    if "M" in costStr:
        return float(non_decimal.sub("", costStr)) * 1_000_000

    return float(non_decimal.sub("", costStr))


def select_wave(driver, wave: int):
    try:
        wave_selector = Select(
            driver.find_element(By.NAME, f"nwy_seatconfigurator_wave_{wave-1}_selector")
        )
        wave_selector.select_by_visible_text(str(wave))
        return wave
    except NoSuchElementException:
        print(f"No config for wave: {wave}")


def read_route_stats(source: str, destination: str):
    stats_path = f"tmp/{source}/{destination}.json"
    if not os.path.exists(stats_path):
        raise Exception(f"Can't find stats at {stats_path}")

    with open(stats_path, "r") as f:
        return RouteStats.from_json(f.read())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "hub", help="Enter HUB name you need to extract route stats for eg: CGK"
    )
    parser.add_argument(
        "destinations",
        help="""
            List of destination airport code (comma seperated)
            eg: TFS,ZRH,AGP,CPH,ARN,GVA
        """,
    )
    parser.add_argument(
        "--aircraft_make",
        "-m",
        help="Aircraft maker name as per Airline Tycoon",
        default="Airbus",
    )
    parser.add_argument(
        "--aircraft_model",
        "-a",
        help="Aircraft model name for the Aircraft maker",
        default="A380-800",
    )
    args = parser.parse_args()
    try:
        driver = webdriver.Chrome()
        find_seat_config(
            driver,
            args.hub,
            args.destinations.split(","),
            args.aircraft_make,
            args.aircraft_model,
        )
    except Exception:
        traceback.print_exception(*sys.exc_info())
    finally:
        time.sleep(5)
        driver.quit()
