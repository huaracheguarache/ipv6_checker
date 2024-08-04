from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import time
from io import BytesIO
import pycurl
from tenacity import retry, retry_if_exception_type, retry_if_result, stop_after_attempt


@retry(retry=retry_if_exception_type(PlaywrightTimeoutError), stop=stop_after_attempt(3))
def load_page(context, url):
    page = context.new_page()
    response_urls = []
    page.on('response', lambda response: response_urls.append(response.url))
    try:
        page.goto(url, wait_until='load', timeout=25000)
    except PlaywrightTimeoutError:
        page.close()
        raise PlaywrightTimeoutError
    else:
        # Wait 5 seconds for any additional resources to load before closing the page.
        time.sleep(5)
        page.close()

    return response_urls


def is_timeout(result):
    return result == 'TIMEOUT'


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
