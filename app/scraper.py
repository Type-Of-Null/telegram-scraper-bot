from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FFOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FFService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
import time
from urllib.parse import urljoin, urlparse


def _make_driver(
    use_chrome: bool = True, headless: bool = True, window_size: str = "1200,800"
):
    if use_chrome:
        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-gpu")
        opts.add_argument(f"--window-size={window_size}")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        driver_path = ChromeDriverManager().install()
        service = ChromeService(driver_path)
        driver = webdriver.Chrome(service=service, options=opts)
    else:
        opts = FFOptions()
        if headless:
            opts.add_argument("--headless")
        width, height = window_size.split(",")
        opts.add_argument(f"--width={width}")
        opts.add_argument(f"--height={height}")

        driver_path = GeckoDriverManager().install()
        service = FFService(driver_path)
        driver = webdriver.Firefox(service=service, options=opts)
    return driver


def scrape_headlines(
    news_url: str,
    max_items: int = 10,
    use_chrome: bool = True,
    headless: bool = True,
    timeout: int = 12,
):
    driver = None
    try:
        driver = _make_driver(use_chrome=use_chrome, headless=headless)
        driver.set_page_load_timeout(timeout)
        driver.get(news_url)
        time.sleep(1.0)

        anchors = driver.find_elements(By.TAG_NAME, "a")
        seen = set()
        results = []

        base_domain = urlparse(news_url).netloc

        for a in anchors:
            try:
                href = a.get_attribute("href")
                text = (a.text or "").strip()
                if not href or not text:
                    continue
                # нормализуем относительные ссылки
                if href.startswith("/"):
                    href = urljoin(news_url, href)
                parsed = urlparse(href)
                # оставляем ссылки того же домена
                if parsed.netloc and base_domain not in parsed.netloc:
                    continue
                # фильтрация по длине текста
                if len(text) < 15 or len(text) > 300:
                    continue
                key = (text, href)
                if key in seen:
                    continue
                seen.add(key)
                results.append((text, href))
                if len(results) >= max_items:
                    break
            except Exception:
                continue

        # git поиск по заголовкам h1/h2/h3
        if len(results) < max_items:
            headers = driver.find_elements(By.XPATH, "//h1|//h2|//h3")
            for h in headers:
                try:
                    ancestor = h.find_element(By.XPATH, "./ancestor::a[1]")
                    if ancestor:
                        href = ancestor.get_attribute("href")
                        text = h.text.strip()
                        if href and text and (text, href) not in seen:
                            parsed = urlparse(href)
                            if base_domain in parsed.netloc:
                                seen.add((text, href))
                                results.append((text, href))
                                if len(results) >= max_items:
                                    break
                except Exception:
                    continue

        return results[:max_items]
    except (WebDriverException, TimeoutException) as e:
        raise RuntimeError(f"Selenium error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
