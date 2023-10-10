import string
import time
import requests
import langdetect
import os

from typing import Tuple, List, Dict
from bs4 import BeautifulSoup
from datetime import datetime

def generate_timestamp() -> str:
	"""
	Returns current system time.
	"""
	# Get the current time
	current_datetime = datetime.now()

	# Format the date and time as a string
	timestamp = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")

	return timestamp

def get_pages_number(url: str) -> int:
	"""
	Get the highest page number per given letter.
	Used in cooperation with 'create_lut_pagination' method.
	"""

	max_page = 0
	try: 
		req = requests.get(url)
		req.raise_for_status()
	except requests.exceptions.RequestException as e:
		print(f"An error occured: {e}")
		return max_page

	if req.ok:
		soup = BeautifulSoup(req.content, 'lxml')

		if soup:
			for page in soup.find_all(class_='page-link'):
				if page.text.isnumeric() and int(page.text) > max_page:
					max_page = int(page.text)

	return max_page

def create_lut_pagination() -> dict:
	"""
	Creates a look-up table for each letter containing max page number
	"""

	alphabet = list(string.ascii_uppercase) + ['pozostale']

	lut_pages = {}

	for letter in alphabet:
			time.sleep(1)
			url = f"https://www.tekstowo.pl/artysci_na,{letter}.html"

			try:
				lut_pages[letter] = get_pages_number(url)
				print(f"Letter {letter} has {lut_pages[letter]} pages of artists.")
			except Exception as e:
				print(f"An error has occured for letter {letter}: {e}")
	
	return lut_pages

def get_artists(letter: str, max_page_per_letter: Dict[str, int]) -> Tuple[List[str], int]:
	"""
	Scrape all of the artists starting with a given letter in the alphabet.
	"""
	
	urls = []
	limit = max_page_per_letter[letter]+1

	for page in range(1, limit):

		url = f"https://www.tekstowo.pl/artysci_na,{letter},strona,{page}.html"

		try:
			time.sleep(2)
			response = requests.get(url)
			if response.ok:
				soup = BeautifulSoup(response.content, 'lxml')
				for link in soup.find_all('a'):
					item = link.get('href')
					if type(item) == str and 'piosenki_' in item:
						urls.append('https://tekstowo.pl' + item)
		except Exception as e:
			print(e)
		print(f"{letter}: Visited {page}/{limit-1}")
		
	print(f"{generate_timestamp()}Letter {letter}: collected {len(urls)} artists")
	print(f"Letter {letter} artists collected.")
	return urls, len(urls)

def get_artist_songs(artist_url: str) -> list:
    """
    Extract all the songs from a given artist.
    """
    urls = []
    processed_first_page = False

    while not processed_first_page:
        time.sleep(5)
        try:
            response = requests.get(artist_url)

            # Check for request success
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            songs = soup.find_all(class_='box-przeboje')
            artist = soup.find(class_="col-md-7 col-lg-8 px-0")
            artist = artist.text.split(" (")[0].strip()

            for song in songs:
                song_title_element = song.find(class_='title')

                if song_title_element:
                    if artist in song_title_element.text.strip():
                        song_url = "https://tekstowo.pl" + song_title_element['href']
                        if not ".plpiosenka" in song_url and song_url not in urls and not "dodaj_tekst" in song_url:
                            urls.append(song_url)

            button_next_page = soup.find_all(class_='page-link')
            if button_next_page and len(button_next_page) > 0:
                button_next_page = button_next_page[-1]

                if 'następna' in button_next_page.text.lower():
                    artist_url = "https://tekstowo.pl" + button_next_page['href']
                else:
                    break
            else:
                break

        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the HTTP request: {e}")
            return False

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False
    
    print(f"Artist {artist}, collected {len(urls)} song URLs")
    return urls

def extract_song(song_url: str) -> str, str, str:
	"""
	Scrapes the song (and song_translation if found) and its
	title from a given song_url.
	"""

	song = ""
	song_translation = None

	try:
		response = requests.get(song_url)
		if response.ok:
			# Scrape URL content with BeautifulSoup
			soup = BeautifulSoup(response.content, 'lxml')

			# Song title
			song_title = soup.find(class_='col-lg-7').text.strip()
		
			# Original song
			song_html = soup.find(class_='inner-text')			
			song = song_html.text.strip()

			# Translated version
			transl_html = soup.find('div', id='translation')
			song_translation = transl_html.text.strip().split("\t\t")[0]

	except Exception as e:
		print(e)

	return song, song_translation, song_title

def assess_language(song_text: str) -> str, str:
	"""
	Detect the language of provided song.
	"""
	if not isinstance(song_text, str):
		return False

	else:
		try:
			return langdetect.detect(song_text)
		except langdetect.lang_detect_exception.LangDetectException:
			return False

def save_songs(title: str, song_1: str, song_2: str, lang_1: str, lang_2: str):
	"""
	Save the scraped song with corresponding languages
	and title.
	"""

	# Saving directory
	save_dir = "teksty/"

	# Title cannot have backslash in it
	clean_title = title.replace('/', '-')

	# Original song
	if isinstance(lang_1, str) and len(lang_1) < 3 and len(song_1) > 10:
		song_1_filename = f"{clean_title}__{lang_1.upper()}.txt"
		
		# Save to a file
		with open(os.path.join(save_dir, song_1_filename), 'w', encoding='utf-8') as f:
			f.write(song_1)
			f.close()	
			print(f"{generate_timestamp()} Original successfully saved: {title}")
	else:
		print(f"{generate_timestamp()} Song {title} is too short or has no text.")

	# Translated song
	if isinstance(lang_2, str) and len(lang_2) < 3 and len(song_2) > 10:
		song_2_filename = f"{clean_title}__TRAN__{lang_2.upper()}.txt"

		# Save to a file
		with open(os.path.join(save_dir, song_2_filename), 'w', encoding='utf-8') as f:
			f.write(song_2)
			f.close()
			print(f"{generate_timestamp()} Translation successfully saved: {title}")
	
	else:
		print(f"{generate_timestamp()} Translation not found or empty.")

