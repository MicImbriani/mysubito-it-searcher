import re
from datetime import datetime

EURO_1 = 1
EURO_2 = 2
EURO_3 = 3
EURO_4 = 4
EURO_5 = 5
EURO_6 = 6

additional_info_keys = [
    "condition",
    "registration_date",
    "KM",
    "fuel",
    "transmission_type",
    "emission"
]



def get_additional_info(product):
    '''
        Takes a BeautifulSoup object representing an HTML snippet of a product.
        Returns a dictionary of key:value pair:
            {additional_info: value}
    '''
    all_info = product.find_all('p',class_=re.compile(r'sbt-text-atom'))
    vals = [info.get_text(strip=True) for info in all_info]
    
    # Some ads don't have "emission" field.
    if len(vals) == 5:
        vals.append("NONE")

    return (
        dict(map(lambda i, j: (i, j), additional_info_keys, vals))
        if len(vals) == len(additional_info_keys)
        else None
    )



# def carCondition_check(expCond, cond):
#     return True if cond == "null" or cond == expCond else False

def minRegDate_check(minDate, date):
    # required format: 06/2021
    if len(date) == 4:
        date = "01/"+str(date)
    if minDate == "null" or date == "null":
        # print("minRegDate_check: ", True)
        return True
    minDate_obj = datetime.strptime(minDate, '%m/%Y').date()
    date_obj = datetime.strptime(date, '%m/%Y').date()
    # print("minRegDate_check: ", date_obj >= minDate_obj)
    return True if date_obj >= minDate_obj else False

def maxRegDate_check(maxDate, date):
    # required format: 06/2021
    if maxDate == "null" or date == "null":
        # print("maxRegDate_check: ", True)
        return True
    maxDate_obj = datetime.strptime(maxDate, '%m/%Y').date()
    date_obj = datetime.strptime(date, '%m/%Y').date()
    # print("maxRegDate_check: ", date_obj <= maxDate_obj)
    return True if date_obj <= maxDate_obj else False

def minKM_check(minKM, km):
    # print("minKM_check :", km == "null" or km >= minKM)
    return True if km == "null" or km >= minKM else False

def maxKM_check(maxKM, km):
    # print("maxKM_check :", km == "null" or km <= maxKM)
    return True if km == "null" or km <= maxKM else False

# def fuelType_check(expType, type):
#     return True if type == "null" or type == expType else False

# def transmType_check(expTransmType, type):
#     return True if type == "null" or type == expTransmType else False

def run_car_check(product, minDate, maxDate, minKM, maxKM):
    info = get_additional_info(product)
    title = product.find('h2').string
    
    if info == None:
        return True
    
    if (minRegDate_check(minDate, info["registration_date"]) and
        maxRegDate_check(maxDate, info["registration_date"]) and
        minKM_check(int(minKM), int(re.sub("[^0-9]", "", info["KM"]))) and
        maxKM_check(int(maxKM), int(re.sub("[^0-9]", "", info["KM"])))
    ):
        return True
    else:
        return False