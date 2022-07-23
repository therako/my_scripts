import argparse
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass
from typing import List, Tuple

from dataclasses_json import dataclass_json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

non_decimal = re.compile(r"[^\d.]+")


@dataclass_json
@dataclass
class RouteStat:
    price: int
    demand: int
    remaining_demand: int


@dataclass_json
@dataclass
class RouteStats:
    economy: RouteStat = None
    business: RouteStat = None
    first: RouteStat = None
    cargo: RouteStat = None
    category: int = 0
    distance: int = 0


def login(driver):
    driver.get("http://tycoon.airlines-manager.com/network/")
    username = driver.find_element("id", "username")
    username.send_keys(os.getenv("TYCOON_EMAIL"))
    password = driver.find_element("id", "password")
    password.send_keys(os.getenv("TYCOON_PASSWORD"))
    login = driver.find_element("id", "loginSubmit")
    login.click()


def find_hub_id(driver, hub: str) -> int:
    driver.get("http://tycoon.airlines-manager.com/network/")
    driver.find_elements(By.XPATH, '//*[@id="lineList"]/div')
    hubs = driver.find_elements(
        By.XPATH, '//*[@id="displayRegular"]/div[@class="hubListBox"]/div'
    )
    for hub_element in hubs:
        match = re.search("Hub ([A-Z]{3}) -", hub_element.text)
        if match and match.group(1) == hub:
            return int(
                hub_element.find_element(By.LINK_TEXT, "Hub details")
                .get_attribute("href")
                .split("/")[-1],
            )


def get_all_routes(driver, hub: str, hub_id: int) -> List[str]:
    driver.get(f"http://tycoon.airlines-manager.com/network/showhub/{hub_id}/linelist")
    route_elements = driver.find_elements(By.XPATH, '//*[@id="lineList"]/div')

    destinations = []
    for route_element in route_elements:
        destinations.append(extract_destination(hub, route_element))

    return destinations


def extract_destination(hub: str, route_element) -> str:
    if "lineListBox" in route_element.get_attribute("class"):
        title = route_element.find_element(By.CLASS_NAME, "title").text
        match = re.search("([A-Z]{3}) \/ ([A-Z]{3})", title)
        if match and match.group(1) == hub:
            return match.group(2)


def select_route(driver, route_text: str):
    driver.get(f"https://tycoon.airlines-manager.com/network/")
    routes = Select(driver.find_element(By.CLASS_NAME, "linePicker"))
    routes.select_by_visible_text(route_text)


def get_max_category(driver) -> int:
    max_cat = driver.find_element(By.XPATH, '//*[@id="box2"]/li[1]/b/img[3]')
    return int(non_decimal.sub("", max_cat.get_attribute("alt")))


def get_distance(driver) -> int:
    dist = driver.find_element(By.XPATH, '//*[@id="box2"]/li[2]')
    return int(non_decimal.sub("", dist.text))


def get_route_stats(driver, route_text: str) -> RouteStats:
    select_route(driver, route_text)
    route_stats = RouteStats(
        category=get_max_category(driver), distance=get_distance(driver)
    )

    prices = driver.find_element(By.LINK_TEXT, "Route prices")
    driver.get(prices.get_attribute("href"))
    priceLists = driver.find_elements(
        By.XPATH, '//*[@id="marketing_linePricing"]/div[@class="box2"]/div'
    )

    for priceList in priceLists:
        route_stats.__setattr__(*extract_route_stat(priceList))

    return route_stats


def extract_route_stat(priceList) -> Tuple[str, RouteStat]:
    return (
        priceList.find_element(By.CLASS_NAME, "title")
        .text.replace("class", "")
        .strip()
        .lower(),
        RouteStat(
            price=non_decimal.sub(
                "",
                priceList.find_element(By.CLASS_NAME, "price")
                .find_element(By.TAG_NAME, "b")
                .text,
            ),
            demand=non_decimal.sub(
                "", priceList.find_element(By.CLASS_NAME, "demand").text
            ),
            remaining_demand=non_decimal.sub(
                "", priceList.find_element(By.CLASS_NAME, "paxLeft").text
            ),
        ),
    )


def save_output(hub: str, route: str, route_stats: RouteStats):
    if not os.path.exists(f"tmp/{hub}"):
        os.makedirs(f"tmp/{hub}")
    with open(f"tmp/{hub}/{route}.json", "w+") as f:
        f.write(route_stats.to_json())


def is_extracted(hub: str, route: str):
    return os.path.exists(f"tmp/{hub}/{route}.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "hub", help="Enter HUB name you need to extract route stats for"
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Force extract all routes for HUB"
    )
    args = parser.parse_args()
    try:
        driver = webdriver.Chrome()
        login(driver)
        hub_id = find_hub_id(driver, args.hub)
        routes = list(filter(None, get_all_routes(driver, args.hub, hub_id)))
        print(f"All routes from HUB {args.hub}: {','.join(routes)}")
        for route in routes:
            if route and (not is_extracted(args.hub, route) or args.force):
                route_name = f"{args.hub} - {route}"
                route_stats = get_route_stats(driver, route_name)
                save_output(args.hub, route, route_stats)
                print(f"{route_name}: \n\t {route_stats}")
    except Exception:
        traceback.print_exception(*sys.exc_info())
    finally:
        time.sleep(5)
        driver.quit()
