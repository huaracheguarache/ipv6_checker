import numpy as np
from tools import load_page, curl_ipv6_request
from urllib.parse import urlparse
import json
from playwright.sync_api import sync_playwright

municipalities, urls = np.loadtxt('/input/kommuner.csv',
                                  skiprows=1,
                                  usecols=[1, 5],
                                  delimiter=',',
                                  dtype='str',
                                  unpack=True)

p = sync_playwright().start()
browser = p.firefox.launch()
context = browser.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0',
                              ignore_https_errors=True)

data = {}
for municipality, url in zip(municipalities, urls):
    print(f'Getting {municipality}...', end='')

    own = []
    if 'www.' in url:
        own.append([url, curl_ipv6_request('https://' + url)])
        own.append([url.replace('www.', ''), curl_ipv6_request('https://' + url.replace('www.', ''))])
    else:
        own.append(['www.' + url, curl_ipv6_request('https://www.' + url)])
        own.append([url, curl_ipv6_request('https://' + url)])

    responses = load_page(context, 'https://' + url)

    netlocs = []
    for response in responses:
        netloc = urlparse(response).netloc
        # Avoid appending the netloc of municipality to tertiary netloc list.
        if netloc and netloc not in own[0][0]:
            netlocs.append(netloc)

    unique_netlocs = sorted(set(netlocs))
    data[str(municipality)] = dict(own=own, tertiary=unique_netlocs)
    print('Finished!')

p.stop()

tertiary = []
for netloc_list in data.values():
    tertiary += netloc_list['tertiary']

unique_tertiary, counts = np.unique(np.array(tertiary), return_counts=True)
sorted_index = np.argsort(unique_tertiary)

ipv6_status = []
for netloc in unique_tertiary:
    ipv6_status.append(curl_ipv6_request('https://' + netloc))

tertiary_info = []
for i in sorted_index:
    tertiary_info.append([unique_tertiary[i], ipv6_status[i], int(counts[i])])

data['tertiary_info'] = tertiary_info

json_data = json.dumps(data, indent=4, ensure_ascii=False)

with open('/output/data.json', 'w') as outfile:
    outfile.write(json_data)
