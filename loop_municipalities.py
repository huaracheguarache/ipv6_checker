import numpy as np
from tools import curl_ipv6_request, TertiaryDomains
import json

municipalities, urls = np.loadtxt('/input/kommuner.csv',
                                  skiprows=1,
                                  usecols=[1, 5],
                                  delimiter=',',
                                  dtype='str',
                                  unpack=True)

municipalities = list(municipalities)
urls = list(urls)

own_domains = {}
for municipality, url in zip(municipalities, urls):
    print(f'Getting {municipality}...', end='')

    own = []
    if 'www.' in url:
        own.append([url, curl_ipv6_request('https://' + url)])
        own.append([url.replace('www.', ''), curl_ipv6_request('https://' + url.replace('www.', ''))])
    else:
        own.append(['www.' + url, curl_ipv6_request('https://www.' + url)])
        own.append([url, curl_ipv6_request('https://' + url)])

    own_domains[municipality] = own

    print('Finished!')

tertiary_domains = TertiaryDomains(municipalities, urls)
tertiary_domains.retry_failed(3, 3600)

data = {}
for municipality in municipalities:
    data[municipality] = {'own': own_domains[municipality], 'tertiary': tertiary_domains.results[municipality]}

tertiary = []
for netloc_list in tertiary_domains.results.values():
    tertiary += netloc_list

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
