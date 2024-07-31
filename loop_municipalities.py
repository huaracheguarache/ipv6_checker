import numpy as np
from tools import get_response_urls, curl_ipv6_request
from urllib.parse import urlparse
import json

municipalities, urls = np.loadtxt('/input/kommuner.csv',
                                  skiprows=1,
                                  usecols=[1, 5],
                                  delimiter=',',
                                  dtype='str',
                                  unpack=True)

municipality_netlocs = {}
for municipality, url in zip(municipalities, urls):
    print(f'Getting {municipality}...', end='')

    own_netlocs = dict()
    if 'www.' in url:
        own_netlocs['netlocs'] = [url]
        own_netlocs['ipv6_statuses'] = [curl_ipv6_request('https://' + url)]
        own_netlocs['netlocs'].append(url.replace('www.', ''))
        own_netlocs['ipv6_statuses'].append(curl_ipv6_request('https://'
                                                              + url.replace('www.', '')))
    else:
        own_netlocs['netlocs'] = ['www.' + url]
        own_netlocs['ipv6_statuses'] = [curl_ipv6_request('https://www.' + url)]
        own_netlocs['netlocs'].append(url)
        own_netlocs['ipv6_statuses'].append(curl_ipv6_request('https://' + url))

    response_urls = get_response_urls('https://' + url)

    netlocs = []
    for response_url in response_urls:
        netloc = urlparse(response_url).netloc
        # Avoid appending the netloc of municipality to tertiary netloc list.
        if netloc and netloc not in own_netlocs['netlocs'][0]:
            netlocs.append(netloc)

    unique_netlocs = sorted(set(netlocs))
    municipality_netlocs[str(municipality)] = dict(own_netlocs=own_netlocs, tertiary_netlocs=unique_netlocs)
    print('Finished!')

full_netloc_collection = []
for netloc_list in municipality_netlocs.values():
    full_netloc_collection += netloc_list['tertiary_netlocs']

unique_netlocs, counts = np.unique(np.array(full_netloc_collection), return_counts=True)
sorted_index = np.argsort(unique_netlocs)

ipv6_status = []
for netloc in unique_netlocs:
    ipv6_status.append(curl_ipv6_request('https://' + netloc))

counts_and_ipv6 = dict(tertiary_netlocs=unique_netlocs[sorted_index].tolist(),
                       counts=counts[sorted_index].tolist(),
                       ipv6_statuses=np.array(ipv6_status)[sorted_index].tolist())

data = dict(individual_municipalities=municipality_netlocs, counts_and_ipv6=counts_and_ipv6)
json_data = json.dumps(data, indent=4, ensure_ascii=False)

with open('/output/data.json', 'w') as outfile:
    outfile.write(json_data)
