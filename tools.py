from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from io import BytesIO
import pycurl
from tenacity import retry, retry_if_exception_type, retry_if_result, stop_after_attempt


def close_browser(browser):
    # Sleeping for 5 seconds to wait for additional requests.
    time.sleep(5)
    browser.close()


@retry(retry=retry_if_exception_type(PlaywrightTimeoutError), stop=stop_after_attempt(3))
def get_response_urls(url):
    with sync_playwright() as p:
        browser = p.firefox.launch()
        context = browser.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101'
                                                 ' Firefox/127.0',
                                      ignore_https_errors=True)
        page = context.new_page()

        response_urls = []
        page.on('response', lambda response: response_urls.append(response.url))
        page.goto(url, timeout=25000)
        page.on('load', close_browser(browser))

    return response_urls


def is_timeout(result):
    return result is 'TIMEOUT'


def return_last_value(retry_state):
    return retry_state.outcome.result()


@retry(retry=retry_if_result(is_timeout), stop=stop_after_attempt(3), retry_error_callback=return_last_value)
def curl_ipv6_request(url):
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V6)
    c.setopt(pycurl.TIMEOUT, 10)
    c.setopt(pycurl.SSL_VERIFYPEER, 0)
    c.setopt(pycurl.SSL_VERIFYHOST, 0)
    c.setopt(pycurl.WRITEDATA, buffer)

    try:
        c.perform()
    except pycurl.error as error:
        c.close()
        if error.args[0] == 28:
            return 'TIMEOUT'
        elif error.args[0] == 6:
            return 'NOT_RESOLVABLE'
        elif error.args[0] == 7:
            return 'NO_ROUTE_TO_HOST'
        else:
            return f'{error.args[0]}: {error.args[1]}'
    else:
        c.close()
        return 'OK'
