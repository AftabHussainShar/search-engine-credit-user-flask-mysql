import requests
from bs4 import BeautifulSoup

# URL to fetch data from
url = 'https://www.fastpeoplesearch.com/address/123-RICHH-ST-WAXAHACHIE_TX-75165~8799'

# Send HTTP GET request
response = requests.get(url)

# Check if request was successful
if response.status_code == 200:
    # Parse HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all divs with class 'card'
    cards = soup.find_all('div', class_='card')

    # Iterate over each card and find span with class 'grey' containing 'San Antonio, TX'
    for card in cards:
        span = card.find('span', class_='grey')
        print(span.text)  
        print('--------------------')
else:
    print(f'Failed to fetch data from {url}. Status code: {response.status_code}')
