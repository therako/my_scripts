import traceback
import time
import os
import sys
from retry import retry

from route import RouteStats, non_decimal
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
)
from typing import List
import pandas as pd
from dataclasses import dataclass

AIRCRAFTMAKE = "Airbus"
AIRCRAFTMODEL = "A380-800 (903 km/h)"

HUB = "CGK"
To_DESTINATIONS = %w(
TFS
ZRH
AGP
CPH
ARN
GVA
)


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


def find_seat_config(driver: webdriver.Remote, source: str, destinations: List[str]):
    driver.get("https://destinations.noway.info/en/seatconfigurator/index.html")
    cf_aircraftmake = Select(driver.find_element("id", "cf_aircraftmake"))
    cf_aircraftmake.select_by_visible_text(AIRCRAFTMAKE)
    cf_aircraftmodel = Select(driver.find_element("id", "cf_aircraftmodel"))
    cf_aircraftmodel.select_by_visible_text(AIRCRAFTMODEL)
    change_to_airport_codes(driver)

    for destination in destinations:
        fillin_route_stats(driver, source, destination)

    calculate_seat_config(driver)
    wave_stats = scan_seat_configs()
    show_best_configs(wave_stats)


def show_best_configs(wave_stats):
    df = pd.DataFrame(wave_stats)
    df.loc[:, "total_turnover_str"] = (
        df["total_turnover"].astype(int).map("{:,}".format)
    )
    print(f"Best by ROI:")
    print(df.iloc[df["roi"].idxmax()])
    print(f"Best by Turnover:")
    print(df.iloc[df["total_turnover"].idxmax()])

    print("*** ALL CONFIGS ***")
    print(df)


@retry((NoSuchElementException, ElementClickInterceptedException), delay=5, tries=6)
def calculate_seat_config(driver):
    driver.find_element("id", "calculate_button").click()


@retry(ElementClickInterceptedException, delay=5, tries=6)
def change_to_airport_codes(driver):
    try:
        driver.find_element(By.LINK_TEXT, "Quick Entry").click()
        driver.find_element(By.LINK_TEXT, "Quick Entry").click()
    except NoSuchElementException:
        pass


def fillin_route_stats(driver, source: str, destination: str):
    cf_hub_src = driver.find_element("id", "cf_hub_src")
    cf_hub_src.send_keys(source)
    cf_hub_dst = driver.find_element("id", "cf_hub_dst")
    cf_hub_dst.send_keys(destination)

    route_stats: RouteStats = read_route_stats(source, destination)
    driver.find_element("id", "auditprice_eco").send_keys(route_stats.economy.price)
    driver.find_element("id", "auditprice_bus").send_keys(route_stats.business.price)
    driver.find_element("id", "auditprice_first").send_keys(route_stats.first.price)
    driver.find_element("id", "auditprice_cargo").send_keys(route_stats.cargo.price)

    driver.find_element("id", "demand_eco").send_keys(route_stats.economy.demand)
    driver.find_element("id", "demand_bus").send_keys(route_stats.business.demand)
    driver.find_element("id", "demand_first").send_keys(route_stats.first.demand)
    driver.find_element("id", "demand_cargo").send_keys(route_stats.cargo.demand)

    add_to_circuit(driver)


@retry(ElementClickInterceptedException, delay=5, tries=6)
def add_to_circuit(driver):
    driver.find_element("id", "add2circuit_button").click()


def scan_seat_configs(maxWave=10):
    wave_stats = []
    for wave in range(1, maxWave):
        if wave != 1:
            if not select_wave(driver, wave):
                break

        wave_stats.append(extract_wave_config(driver, wave))

    return wave_stats


@retry(NoSuchElementException, delay=5, tries=2)
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
    try:
        driver = webdriver.Chrome()
        find_seat_config(driver, HUB, To_DESTINATIONS)
    except Exception:
        traceback.print_exception(*sys.exc_info())
    finally:
        pass
        time.sleep(20)
        driver.quit()
