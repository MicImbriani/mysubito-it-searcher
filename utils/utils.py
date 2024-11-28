def minPrice_check(minPrice, price):
    return True if minPrice == "null" or price == "Unknown price" or price>=int(minPrice) else False

def maxPrice_check(maxPrice, price):
    return True if maxPrice == "null" or price == "Unknown price" or price<=int(maxPrice) else False