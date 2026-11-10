"""Scrape a word-frequency ranking (with per-meaning details) from kimchi-reader.app.

Needs the `scrape` extra (`uv sync --extra scrape`) and Chrome. The page is
driven through its UI, so the XPaths below are tied to the site's current
layout and will break when it changes. Check the site's terms before
scraping and keep the delay polite; scraped data is for personal use and is
not redistributed with this repository.
"""

from __future__ import annotations

import csv
import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

URL = "https://kimchi-reader.app/explore/freq/words"
_POPUP_MEANINGS_XPATH = "/html/body/div/div[1]/div[1]/div[2]/div[2]/div[2]/div[3]/div[1]/div/div[4]/div[2]/div[1]/div/div[2]"  # noqa: E501
_MEANING_ROW_CSS = "div.\\[display\\:contents\\]"
_WORD_LIST_XPATH = "/html/body/div/div[1]/div[1]/div[2]/div[2]/div[2]/div[2]/div/div[4]"
_NEXT_BUTTON_XPATH = (
    "/html/body/div/div[1]/div[1]/div[2]/div[2]/div[2]/div[2]/div/div[5]/div[3]/button[3]"
)

FIELDNAMES = ["Rank", "Word", "Meaning_Num", "Short_Meaning", "Long_Meaning", "Stars"]


@dataclass
class Meaning:
    number: str
    short: str
    long: str
    stars: int


@dataclass
class ScrapedRow:
    rank: str  # "<word rank>.<meaning index>"
    word: str
    meaning: Meaning | None


def _selenium():
    try:
        from selenium import webdriver
        from selenium.common.exceptions import NoSuchElementException, TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError as e:  # pragma: no cover - depends on optional extra
        raise SystemExit("Scraping needs Selenium: install with `uv sync --extra scrape`.") from e
    return webdriver, NoSuchElementException, TimeoutException, By, EC, WebDriverWait


def _star_count(container, idx: int, By) -> int:
    try:
        stars_rows = container.find_elements(By.CSS_SELECTOR, "div[flex][flex-row][justify-end]")
        if idx <= len(stars_rows):
            return len(
                stars_rows[idx - 1].find_elements(By.CSS_SELECTOR, "div.i-mingcute-star-fill")
            )
    except Exception as e:  # layout drift: don't abort the whole scrape
        logger.warning("could not read stars: %s", e)
    return 0


def _long_meaning(row, number: str, short: str, By) -> str:
    for div in row.find_elements(By.TAG_NAME, "div"):
        if not (
            div.get_attribute("pr-2") or div.get_attribute("c-orange") or div.get_attribute("flex")
        ):
            text = div.text.strip()
            if text and text not in (number, short):
                return text
    return ""


def _word_meanings(driver, element, delay: float) -> list[Meaning]:
    _, NoSuchElement, Timeout, By, EC, Wait = _selenium()
    meanings: list[Meaning] = []
    try:
        element.click()
        wait = Wait(driver, 10)
        container = wait.until(EC.presence_of_element_located(("xpath", _POPUP_MEANINGS_XPATH)))
        time.sleep(3 * delay)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, _MEANING_ROW_CSS)))
        for idx, row in enumerate(container.find_elements(By.CSS_SELECTOR, _MEANING_ROW_CSS), 1):
            try:
                number = row.find_element(By.CSS_SELECTOR, "div[pr-2]").text.strip()
                try:
                    short = row.find_element(By.CSS_SELECTOR, "div[c-orange]").text.strip()
                except NoSuchElement:
                    short = ""
                meanings.append(
                    Meaning(
                        number,
                        short,
                        _long_meaning(row, number, short, By),
                        _star_count(container, idx, By),
                    )
                )
            except Exception as e:
                logger.warning("meaning %d failed: %s", idx, e)
        time.sleep(delay)
        try:  # click outside to close the popup
            driver.execute_script("arguments[0].click();", driver.find_element(By.TAG_NAME, "body"))
        except Exception:
            pass
        time.sleep(delay)
    except Timeout:
        logger.warning("timed out waiting for the meanings popup")
    except Exception as e:
        logger.warning("could not read meanings: %s", e)
    return meanings


def scrape(
    max_pages: int = 100, delay: float = 0.5, with_meanings: bool = True
) -> list[ScrapedRow]:
    """Scrape up to `max_pages` pages of the frequency list.

    `delay` (seconds) scales every pause; raise it to be gentler on the site.
    """
    webdriver, NoSuchElement, _, By, EC, Wait = _selenium()
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    rows: list[ScrapedRow] = []
    try:
        driver.get(URL)
        Wait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[kr-lemma-item]")))
        time.sleep(6 * delay)
        for page in range(1, max_pages + 1):
            logger.info("scraping page %d", page)
            time.sleep(4 * delay)
            try:
                items = driver.find_element(By.XPATH, _WORD_LIST_XPATH).find_elements(
                    By.XPATH, "./div"
                )
            except NoSuchElement:
                logger.error("word list container not found; the site layout probably changed")
                break
            for div in items:
                try:
                    rank = div.text.split("\n")[0].strip().rstrip(".").split(".")[0].strip()
                    element = div.find_element(By.CSS_SELECTOR, "[kr-lemma-item]")
                    word = element.text.strip()
                    if not (rank and word):
                        continue
                    meanings = _word_meanings(driver, element, delay) if with_meanings else []
                    if meanings:
                        rows += [
                            ScrapedRow(f"{rank}.{i}", word, m) for i, m in enumerate(meanings, 1)
                        ]
                    else:
                        rows.append(ScrapedRow(f"{rank}.1", word, None))
                    time.sleep(delay)
                except Exception as e:
                    logger.warning("skipping an item: %s", e)
            try:
                nxt = driver.find_element(By.XPATH, _NEXT_BUTTON_XPATH)
            except NoSuchElement:
                logger.info("no next button; done")
                break
            if nxt.get_attribute("disabled"):
                logger.info("reached the last page")
                break
            driver.execute_script("arguments[0].scrollIntoView(true);", nxt)
            time.sleep(2 * delay)
            nxt.click()
            time.sleep(6 * delay)
    finally:
        driver.quit()
    return rows


def write_csv(rows: list[ScrapedRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="|", lineterminator="\n")
        writer.writerow(FIELDNAMES)
        for r in rows:
            m = r.meaning
            writer.writerow(
                [
                    r.rank,
                    r.word,
                    m.number if m else "1",
                    m.short if m else "",
                    m.long if m else "",
                    m.stars if m else 0,
                ]
            )
