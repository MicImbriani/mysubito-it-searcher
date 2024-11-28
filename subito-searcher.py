#!/usr/bin/env python3.7

import os
import re
import json
import argparse
import requests
import platform
import requests
import time as t
from bs4 import BeautifulSoup, Tag
from datetime import datetime, time

from utils.utils import *
from utils.cars_utils import *
from utils.BLACKLIST import BLACKLIST

parser = argparse.ArgumentParser()
parser.add_argument("--add", dest='name', help="name of new tracking to be added")
parser.add_argument("--url", help="url for your new tracking's search query")
parser.add_argument("--minPrice", help="minimum price for the query")
parser.add_argument("--maxPrice", help="maximum price for the query")
parser.add_argument("--delete", help="name of the search you want to delete")
parser.add_argument('--refresh', '-r', dest='refresh', action='store_true', help="refresh search results once")
parser.set_defaults(refresh=False)
parser.add_argument('--daemon', '-d', dest='daemon', action='store_true', help="keep refreshing search results forever (default delay 120 seconds)")
parser.set_defaults(daemon=False)
parser.add_argument('--activeHour', '-ah', dest='activeHour', help="Time slot. Hour when to be active in 24h notation")
parser.add_argument('--pauseHour', '-ph', dest='pauseHour', help="Time slot. Hour when to pause in 24h notation")
parser.add_argument('--delay', dest='delay', help="delay for the daemon option (in seconds)")
parser.set_defaults(delay=120)
parser.add_argument('--list', dest='list', action='store_true', help="print a list of current trackings")
parser.set_defaults(list=False)
parser.add_argument('--short_list', dest='short_list', action='store_true', help="print a more compact list")
parser.set_defaults(short_list=False)
parser.add_argument('--tgoff', dest='tgoff', action='store_true', help="turn off telegram messages")
parser.set_defaults(tgoff=False)
parser.add_argument('--notifyoff', dest='win_notifyoff', action='store_true', help="turn off windows notifications")
parser.set_defaults(win_notifyoff=False)
parser.add_argument('--addtoken', dest='token', help="telegram setup: add bot API token")
parser.add_argument('--addchatid', dest='chatid', help="telegram setup: add bot chat id")
parser.add_argument('--alt_msg', dest='alt_msg', action='store_true', help="shorter telegram message")
# CARS INFO
parser.add_argument('--cars_info', dest='cars_info', action='store_true', help="expand filter options with additional info")
# parser.add_argument("--condition", help="expected condition for item")
parser.add_argument("--minDate", default="null", help="minumun registration date for the query")
parser.add_argument("--maxDate", default="null", help="maximum registration date for the query")
parser.add_argument("--minKM", default="1", help="maximum KM for the query")
parser.add_argument("--maxKM", default="1000000", help="minimum KM for the query")


args = parser.parse_args()

queries = dict()
apiCredentials = dict()
dbFile = "searches.tracked"
telegramApiFile = "telegram_api_credentials"

# Windows notifications
if platform.system() == "Windows":
    from win10toast import ToastNotifier
    toaster = ToastNotifier()


# load from file
def load_queries():
    '''A function to load the queries from the json file'''
    global queries
    global dbFile
    if not os.path.isfile(dbFile):
        return

    with open(dbFile) as file:
        queries = json.load(file)

def load_api_credentials():
    '''A function to load the telegram api credentials from the json file'''
    global apiCredentials
    global telegramApiFile
    if not os.path.isfile(telegramApiFile):
        return

    with open(telegramApiFile) as file:
        apiCredentials = json.load(file)


def print_queries():
    '''A function to print the queries'''
    global queries
    #print(queries, "\n\n")

    for search in queries.items():
        print("\nsearch: ", search[0])
        for query_url in search[1]:
            print("query url:", query_url)
            for url in search[1].items():
                for minP in url[1].items():
                    for maxP in minP[1].items():
                        for result in maxP[1].items():
                            print("\n", result[1].get('title'), ":", result[1].get('price'), "-->", result[1].get('location'))
                            print(" ", result[0])


# printing a compact list of trackings
def print_sitrep():
    '''A function to print a compact list of trackings'''
    global queries
    i = 1
    for search in queries.items():
        print('\n{}) search: {}'.format(i, search[0]))
        for query_url in search[1].items():
            for minP in query_url[1].items():
                for maxP in minP[1].items():
                    print("query url:", query_url[0], " ", end='')
                    if minP[0] !="null":
                        print(minP[0],"<", end='')
                    if minP[0] !="null" or maxP[0] !="null":
                        print(" price ", end='')
                    if maxP[0] !="null":
                        print("<", maxP[0], end='')
                    print("\n")

        i+=1

def refresh(notify):
    '''A function to refresh the queries

    Arguments
    ---------
    notify: bool
        whether to send notifications or not

    Example usage
    -------------
    >>> refresh(True)   # Refresh queries and send notifications
    >>> refresh(False)  # Refresh queries and don't send notifications
    '''
    global queries
    try:
        for search in queries.items():
            for url in search[1].items():
                for minP in url[1].items():
                    for maxP in minP[1].items():
                        run_query(url[0], search[0], notify, minP[0], maxP[0])
    except requests.exceptions.ConnectionError:
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " ***Connection error***")
    except requests.exceptions.Timeout:
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " ***Server timeout error***")
    except requests.exceptions.HTTPError:
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " ***HTTP error***")


def delete(toDelete):
    '''A function to delete a query

    Arguments
    ---------
    toDelete: str
        the query to delete

    Example usage
    -------------
    >>> delete("query")
    '''
    global queries
    queries.pop(toDelete)

def check_product_criteria(product, title, price, minPrice, maxPrice):
    '''
        A function to run checks on query criteria.
    '''
    for word in str(title.string).split(" "):
        if word.lower() in BLACKLIST:
            return False

    if args.cars_info:
        try:
            cars_info_match = run_car_check(product, minDate=args.minDate, maxDate=args.maxDate, minKM=args.minKM, maxKM=args.maxKM)
            if not cars_info_match:
                return False
        except:
            pass
    
    price_match = minPrice_check(minPrice=minPrice, price=price) and maxPrice_check(maxPrice=maxPrice, price=price)
    return True if price_match else False

def run_query(url, name, notify, minPrice, maxPrice):
    '''A function to run a query

    Arguments
    ---------
    url: str
        the url to run the query on
    name: str
        the name of the query
    notify: bool
        whether to send notifications or not
    minPrice: str
        the minimum price to search for
    maxPrice: str
        the maximum price to search for

    Example usage
    -------------
    >>> run_query("https://www.subito.it/annunci-italia/vendita/usato/?q=auto", "query", True, 100, "null")
    '''
    print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " running query (\"{}\" - {})...".format(name, url))

    products_deleted = False

    global queries
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')

    product_list_items = soup.find_all('div', class_=re.compile(r'item-card'))
    msg = []

    for product in product_list_items:
        # Gather relevant information
        title = product.find('h2').string
        link = product.find('a').get('href')

        try:
            price=product.find('p',class_=re.compile(r'price')).contents[0]
            # check if the span tag exists
            price_soup = BeautifulSoup(price, 'html.parser')
            if type(price_soup) == Tag:
                continue
            #at the moment (20.5.2021) the price is under the 'p' tag with 'span' inside if shipping available
            price = int(price.replace('.','')[:-2])
        except:
            price = "Unknown price"

        sold = product.find('span',re.compile(r'item-sold-badge'))

        # check if the product has already been sold
        if sold != None:
            # if the product has previously been saved remove it from the file
            if queries.get(name).get(url).get(minPrice).get(maxPrice).get(link):
                del queries[name][url][minPrice][maxPrice][link]
                products_deleted = True
            continue

        try:
            location = product.find('span',re.compile(r'town')).string + product.find('span',re.compile(r'city')).string
        except:
            print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " Unknown location for item %s" % (title))
            location = "Unknown location"



        # Assess parameters against query criteria
        if check_product_criteria(product, title, price, minPrice, maxPrice):
            if not queries.get(name):   # insert the new search
                queries[name] = {url:{minPrice: {maxPrice: {link: {'title': title, 'price': price, 'location': location}}}}}
                print("\n" + datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " New search added:", name)
                print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " Adding result:", title, "-", price, "-", location)
            else:   # add search results to dictionary
                if not queries.get(name).get(url).get(minPrice).get(maxPrice).get(link):   # found a new element
                    tmp = datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " New element found for "+name+": "+title+" @ "+str(price)+" - "+location+" --> "+link+'\n'
                    alt_msg = (
                        datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + "\n"
                        + str(price) + " €\n"
                        + title + "\n"
                        + location + "\n"
                        + link + '\n'
                    )
                    msg.append(tmp) if not args.alt_msg else msg.append(alt_msg)
                    if args.cars_info:
                        queries[name][url][minPrice][maxPrice][link] ={'title': title, 'price': price, 'location': location}
                    queries[name][url][minPrice][maxPrice][link] ={'title': title, 'price': price, 'location': location}

    if len(msg) > 0:
        if notify:
            # Windows only: send notification
            if not args.win_notifyoff and platform.system() == "Windows":
                global toaster
                toaster.show_toast("New announcements", "Query: " + name)
            if is_telegram_active():
                send_telegram_messages(msg)
            print("\n".join(msg))
            print('\n{} new elements have been found.'.format(len(msg)))
        save_queries()
    else:
        print('\nAll lists are already up to date.')

        # if at least one search was deleted updated the search file
        if products_deleted:
            save_queries()

    # print("queries file saved: ", queries)


def save_queries():
    '''A function to save the queries
    '''
    with open(dbFile, 'w') as file:
        file.write(json.dumps(queries))

def save_api_credentials():
    '''A function to save the telegram api credentials into the telegramApiFile'''
    with open(telegramApiFile, 'w') as file:
        file.write(json.dumps(apiCredentials))

def is_telegram_active():
    '''A function to check if telegram is active, i.e. if the api credentials are present

    Returns
    -------
    bool
        True if telegram is active, False otherwise
    '''
    return not args.tgoff and "chatid" in apiCredentials and "token" in apiCredentials

def send_telegram_messages(messages):
    '''A function to send messages to telegram

    Arguments
    ---------
    messages: list
        the list of messages to send

    Example usage
    -------------
    >>> send_telegram_messages(["message1", "message2"])
    '''
    for msg in messages:
        request_url = "https://api.telegram.org/bot" + apiCredentials["token"] + "/sendMessage?chat_id=" + apiCredentials["chatid"] + "&text=" + msg
        requests.get(request_url)

def in_between(now, start, end):
    '''A function to check if a time is in between two other times

    Arguments
    ---------
    now: datetime
        the time to check
    start: datetime
        the start time
    end: datetime
        the end time

    Example usage
    -------------
    >>> in_between(datetime.now(), datetime(2021, 5, 20, 0, 0, 0), datetime(2021, 5, 20, 23, 59, 59))
    '''
    if start < end:
        return start <= now < end
    elif start == end:
	    return True
    else: # over midnight e.g., 23:30-04:15
        return start <= now or now < end

if __name__ == '__main__':

    ### Setup commands ###

    load_queries()
    load_api_credentials()

    if args.list:
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " printing current status...")
        print_queries()

    if args.short_list:
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " printing quick sitrep...")
        print_sitrep()

    if args.url is not None and args.name is not None:
        run_query(args.url, args.name, False, args.minPrice if args.minPrice is not None else "null", args.maxPrice if args.maxPrice is not None else "null",)
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " Query added.")

    if args.delete is not None:
        delete(args.delete)

    if args.activeHour is None:
        args.activeHour="0"

    if args.pauseHour is None:
        args.pauseHour="0"

    # Telegram setup

    if args.token is not None and args.chatid is not None:
        apiCredentials["token"] = args.token
        apiCredentials["chatid"] = args.chatid
        save_api_credentials()

    ### Run commands ###

    if args.refresh:
        refresh(True)

    print()
    save_queries()


    if args.daemon:
        notify = False # Don't flood with notifications the first time
        while True:
            if in_between(datetime.now().time(), time(int(args.activeHour)), time(int(args.pauseHour))):
                refresh(notify)
                notify = True
                print()
                print(str(args.delay) + " seconds to next poll.")
                save_queries()
            t.sleep(int(args.delay))

