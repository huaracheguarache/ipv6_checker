from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from io import BytesIO
import pycurl
from tenacity import retry, retry_if_exception_type, retry_if_result, stop_after_attempt, RetryError
from urllib.parse import urlparse


class TertiaryDomains:
    def __init__(self, municipalities, urls):
        self.municipalities = municipalities
        self.urls = urls

        p = sync_playwright().start()
        browser = p.firefox.launch()
        context = browser.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101'
                                                 ' Firefox/127.0', ignore_https_errors=True)

        self.results = {}
        self.failed_municipalities = []
        self.failed_urls = []
        for municipality, url in zip(municipalities, urls):
            try:
                print(f'Getting tertiary domains of {municipality}...', end='')
                responses = self._load_page(context, 'https://' + url)
            except RetryError:
                self.results[municipality] = None
                self.failed_municipalities.append(municipality)
                self.failed_urls.append(url)
                print('Failed!')
            else:
                if 'www.' not in url:
                    url = 'www.' + url

                netlocs = []
                for response in responses:
                    netloc = urlparse(response).netloc
                    # Avoid appending the netloc of municipality to tertiary netloc list.
                    if netloc and netloc not in url:
                        netlocs.append(netloc)

                self.results[municipality] = sorted(set(netlocs))
                print('Finished!')

        p.stop()

    @retry(retry=retry_if_exception_type(PlaywrightTimeoutError), stop=stop_after_attempt(3))
    def _load_page(self, context, url):
        page = context.new_page()
        response_urls = []
        page.on('response', lambda response: response_urls.append(response.url))
        try:
            page.goto(url, wait_until='load', timeout=25000)
        except PlaywrightTimeoutError:
            page.close()
            raise
        else:
            # Wait 5 seconds for any additional resources to load before closing the page.
            time.sleep(5)
            page.close()

        return response_urls

    def retry_failed(self, retries: int, delay):
        if self.failed_municipalities:
            for retry in range(retries):
                if self.failed_municipalities:
                    print(f'Retry {retry + 1}')
                    print('Failed municipalities:')
                    for municipality in self.failed_municipalities:
                        print(municipality)

                    print(f'Waiting {delay} seconds.')
                    time.sleep(delay)

                    p = sync_playwright().start()
                    browser = p.firefox.launch()
                    context = browser.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101'
                                                             ' Firefox/127.0', ignore_https_errors=True)

                    for municipality, url in zip(self.failed_municipalities, self.failed_urls):
                        try:
                            print(f'Getting tertiary domains of {municipality}...', end='')
                            responses = self._load_page(context, 'https://' + url)
                        except RetryError:
                            print('Failed!')
                        else:
                            self.failed_municipalities.remove(municipality)
                            self.failed_urls.remove(url)

                            if 'www.' not in url:
                                url = 'www.' + url

                            netlocs = []
                            for response in responses:
                                netloc = urlparse(response).netloc
                                # Avoid appending the netloc of municipality to tertiary netloc list.
                                if netloc and netloc not in url:
                                    netlocs.append(netloc)

                            self.results[municipality] = sorted(set(netlocs))

                            print('Finished!')

                    p.stop()

                else:
                    print('No failed municipalities!')
        else:
            print('No failed municipalities!')


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
