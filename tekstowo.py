# Necessary imports
from typing import Tuple, List, Dict
from datetime import datetime
from bs4 import BeautifulSoup

import os
import argparse
import string
import time
import requests
import langdetect

# Parser config
parser = argparse.ArgumentParser(description="Crawler and scraper dedicated to tekstowo.pl domain")
parser.add_argument("--letter", "--ARTIST_LETTER", help="Choose a letter to scrape the lyrics from (default = Q)", default="", type=str)

args = parser.parse_args()

# Config
ARTIST_LETTER: str = args.letter or "Q" 
SAVE_PROGRESS = 30 # interval of creating a save state file

# TODO:
# create functions: save_progress, load_progress, continue_cycle - DONE
# decide how to save progress: either txt with specific formatting or a json file - DONE
# progress bar?

# Function collection
def generate_timestamp() -> str:
    """
    Returns current system time.
    """
    # Get the current time
    current_datetime = datetime.now()

    # Format the date and time as a string
    timestamp = current_datetime.strftime("%Y-%m-%d, %H:%M:%S")

    return timestamp

def processing_time(start_timestamp: datetime, end_timestamp: datetime) -> Tuple[int, int, int, int]:
    """
    Counts the time that has passed performing a given task.
    """
    processing_time = end_timestamp - start_timestamp
    total_seconds = processing_time.total_seconds()

    days = int(total_seconds // (3600 * 24))
    hours = int((total_seconds // 3600) % 24)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)

    return days, hours, minutes, seconds

def get_max_page_number(url: str) -> int:
    """
    Get the highest page number per given letter.
    Used in cooperation with 'create_lut_pagination' 
    and 'pages_per_letter' method.
    """

    max_page = 0

    try: 
        req = requests.get(url, timeout=60)
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
    per letter in 'alphabet' variable. By default these are all26 letters 
    of the alhpabet with an addition of 'pozostale' entry, which is a 
    domain specific requirement.
    """

    alphabet = list(string.ascii_uppercase) + ['pozostale']

    lut_pages = {}

    for letter in alphabet:
        time.sleep(1)
        url = f"https://www.tekstowo.pl/artysci_na,{letter}.html"

        try:
            lut_pages[letter] = get_max_page_number(url)
            print(f"Letter {letter} has {lut_pages[letter]} pages of artists.")

        except Exception as e:
            print(f"An error has occured for letter {letter}: {e}")
   
    return lut_pages

def pages_per_letter(ARTIST_LETTER: str) -> dict:
    """
    Returns the value of the last page containing the songs
    per artist.
    """

    letter_max_page = 0

    if len(ARTIST_LETTER) < 2:
        ARTIST_LETTER = ARTIST_LETTER.upper()
    
    url = f"https://www.tekstowo.pl/artysci_na,{ARTIST_LETTER}.html"

    try:
        letter_max_page = get_max_page_number(url)
        print(f"Letter {ARTIST_LETTER} has {letter_max_page} pages of artists.")

    except Exception as e:
        print(f"An error has occured for letter {ARTIST_LETTER}: {e}")
   
    return letter_max_page

def get_artists(ARTIST_LETTER: str, max_page_per_letter: Dict[str, int] or int) -> Tuple[List[str], int]:
    """
    Scrape all of the artists starting with a given letter in the alphabet.
    """
    
    urls = []

    if isinstance(max_page_per_letter, dict):
        limit = max_page_per_letter[ARTIST_LETTER]
    elif isinstance(max_page_per_letter, int):
        limit = max_page_per_letter
    else:
        raise ValueError("max_page_per_letter should be either a dictionary \
            with capital letters as keys and integers as values or a plain \
            integer value.")

    for page in range(1, limit + 1):
        url = f"https://www.tekstowo.pl/artysci_na,{ARTIST_LETTER},strona,{page}.html"

        try:
            time.sleep(2)
            response = requests.get(url, timeout=60)
            if response.ok:
                soup = BeautifulSoup(response.content, 'lxml')
                for link in soup.find_all('a'):
                    item = link.get('href')
                    if isinstance(item, str) and 'piosenki_' in item:
                        urls.append('https://tekstowo.pl' + item)

        except Exception as e:
            print(e)

        print(f"{ARTIST_LETTER}: Visited {page}/{limit}")
       
    print(f"{generate_timestamp()}: Letter {ARTIST_LETTER}: collected {len(urls)} artists")
    print(f"Letter {ARTIST_LETTER} artists collected.")

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
            response = requests.get(artist_url, timeout=60)

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

def extract_song(song_url: str) -> Tuple[str, str, str]:
    """
    Scrapes the song (and song_translation if found) and its
    title from a given song_url.
    """

    song = ""
    song_translation = None

    try:
        response = requests.get(song_url, timeout=60)
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

def assess_language(song_text: str) -> str:
    """
    Detect the language of provided song.
    """
    if not isinstance(song_text, str):
        return False

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
    os.makedirs(save_dir, exist_ok=True)

    # Title cannot have backslash in it
    clean_title = title.replace('/', '-')

    # Original song
    if isinstance(lang_1, str) and len(lang_1) < 3 and len(song_1) > 10:
        song_1_filename = f"{clean_title}__{lang_1.upper()}.txt"

        # Save to a file
        with open(os.path.join(save_dir, song_1_filename), 'w', encoding='utf-8') as f:
            f.write(song_1)
            f.close()
            print(f"{generate_timestamp()}: Original successfully saved: {title}")
    else:
        print(f"{generate_timestamp()}: Song {title} is too short or has no text.")

    # Translated song
    if isinstance(lang_2, str) and len(lang_2) < 3 and len(song_2) > 10:
        song_2_filename = f"{clean_title}__TRAN__{lang_2.upper()}.txt"

        # Save to a file
        with open(os.path.join(save_dir, song_2_filename), 'w', encoding='utf-8') as f:
            f.write(song_2)
            f.close()
            print(f"{generate_timestamp()}: Translation successfully saved: {title}")    
    else:
        print(f"{generate_timestamp()}: Translation not found or empty.")

def save_progress(ARTIST_LETTER: str, artist_url: str):
    """
    Saves the last processed url to a txt file, along with the letter
    the script was working on.
    """

    progress_file = f"{ARTIST_LETTER}_progress.txt"
    progress_text = f"{ARTIST_LETTER}###{artist_url}"
    
    with open(os.path.join(progress_file), 'w', encoding='utf-8') as f:
        f.write(progress_text)
        f.close()

    return True

def load_progress(ARTIST_LETTER: str):
    """
    Loads in the data from save file created by the script.
    """

    progress_file = f"{ARTIST_LETTER}_progress.txt"
    
    try:
        with open(os.path.join(progress_file), "r", encoding="utf-8") as f:
            progress_text = f.read()
            f.close()

        visited_url = progress_text.split("###")[1]
        return visited_url

    except Exception as e:
        print(f"An error occured: {e}")
        return False

def main_cycle(ARTIST_LETTER: str):
    """
    Main script cycle - fresh letter, no continuation
    """
    start_timestamp = datetime.now()
    cnt = 0

    # Get max page per given letter
    max_page = pages_per_letter(ARTIST_LETTER)

    # Collect all artists per given letter
    artist_urls, artist_cnt = get_artists(ARTIST_LETTER, max_page)

    # Go through every artist in the URL list
    for artist_url in artist_urls:

        # Collect all song URLs per artist
        artist_songs = get_artist_songs(artist_url)

        try:
            # Delay
            time.sleep(5)

            # Go through all song URLs
            for artist_song in artist_songs:

                # Extract lyrics of given song
                text1, text2, title = extract_song(artist_song)

                # Check the lyrics' language
                lang1 = assess_language(text1)
                lang2 = assess_language(text2)

                # Save songs to txt file
                save_songs(title, text1, text2, lang1, lang2)

        except Exception as e:
            print(f"An error occured: {e}")
        
        # Artist per letter counter
        cnt += 1
        print(f"{generate_timestamp()} : Letter {ARTIST_LETTER}, processed {cnt}/{artist_cnt}")

        # Save current progress
        if save_progress(ARTIST_LETTER, artist_url) and cnt % SAVE_PROGRESS == 0:
            print(f"Progress saved to file - {ARTIST_LETTER}_progress.txt")

    # Finish the cycle
    end_timestamp = datetime.now()
    days, hours, minutes, seconds = processing_time(start_timestamp=start_timestamp,
                                                    end_timestamp=end_timestamp)
    print(f"{ARTIST_LETTER} finished processing.")
    print(f"Processing time: {days}d, {hours}h, {minutes}min {seconds}s")
    
    return True

def continue_cycle(ARTIST_LETTER: str):
    """
    Reads in the last visited URL and continues from this onwards.
    If there is no progress_file, starts the scraping from scratch.
    """
    # Check if there is a progress file
    last_url = load_progress(ARTIST_LETTER)

    if not last_url:
        print("No progress file found, starting from scratch")
        main_cycle(ARTIST_LETTER)

    else:
        start_timestamp = datetime.now()

        # Get max page per given letter
        max_page = pages_per_letter(ARTIST_LETTER)

        # Collect all artists per given letter
        artist_urls, artist_cnt = get_artists(ARTIST_LETTER, max_page)

        # Check where to start from
        item_no = artist_urls.index(last_url, 0, len(artist_urls))
        artist_urls_left = artist_urls[item_no:]

        # Update artist counter
        cnt = item_no
        print(f"Progress file found, starting from URL: {last_url}\n\
            Processed URLs: {item_no}\nURLs left: {len(artist_urls_left) - item_no}")

        # Go through every artist in the URL list
        for artist_url in artist_urls_left:

            # Collect all song URLs per artist
            artist_songs = get_artist_songs(artist_url)

            try:
                # Delay
                time.sleep(5)

                # Go through all song URLs
                for artist_song in artist_songs:

                    # Extract lyrics of given song
                    text1, text2, title = extract_song(artist_song)

                    # Check the lyrics' language
                    lang1 = assess_language(text1)
                    lang2 = assess_language(text2)

                    # Save songs to txt file
                    save_songs(title, text1, text2, lang1, lang2)

            except Exception as e:
                print(f"An error occured: {e}")
            
            # Artist per letter counter
            cnt += 1
            print(f"{generate_timestamp()} : Letter {ARTIST_LETTER}, processed {cnt}/{artist_cnt}")

        # Finish the cycle
        end_timestamp = datetime.now()
        days, hours, minutes, seconds = processing_time(start_timestamp=start_timestamp,
                                                        end_timestamp=end_timestamp)
        print(f"{ARTIST_LETTER} finished processing.")
        print(f"Processing time: {days}d, {hours}h, {minutes}min {seconds}s")
        
        return True

if __name__ == "__main__":
    continue_cycle(ARTIST_LETTER)
