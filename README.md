# Kiwi interview web application

## Task

Your task is to implement a web application that will allow a client to retrieve prices of flights
between source and destination country on a given day. Moreover, the clients of your service
want to see just the cheapest price per source and destination airport. They are interested in
departing from/arriving at only the top 3 popular airports of the selected countries.

### Example output
```json
[
  {
    "src": "ABC",
    "dst": "CBA",
    "price": "102.3"
  },
  {
    "src": "XYZ",
    "dst": "ZYX",
    "price": "28"
  }
]
```

## Deployment
to run all the services please build them first with command `docker-compose build`

Once the build is finished please run `docker-compose up` or if you want to run it in 
detached mode please run `docker-compose up -d`

both commands are run from root of the project

Once everything is running you can test with request as follows

http://localhost/search-flight?source_country=France&destination_country=Italy&departure_date=01/04/2025

you can find apidocs on following address

http://localhost/api/doc/

## Overview
We are using nginx for a webserver and load balancing of requests that are received on
the server. Nginx is using least connections strategy to forward the requests to the container
that is least currently used.

Our application is running on aiohttp webserver where we have single endpoint that can receive
request with 3 parameters.

1. source country
2. destination country
3. date of departure in format of DD-MM-YYYY

I use Redis for caching where we have two different DBs. One is for caching countries to their
respective IDs. This we needed to do because each we needed to get top 3 airports of each country
in both source and destination. Getting those airports I could only with country ID which I could 
get only from separate API. Therefor once I receive top 3 airports of a country I cache it where 
key is country and values is comma separate countries. Here I use expiration of 3 days after value
is cached. Also I have setup the database to use LRU (least recently used) strategy where I have
limited the amount of data to be saved to 200 mb and after that the least recently used key will be
automatically dropped from cache not to overwhelm the environment.

Second DB is for the requested data. If someone would request same destination and source countries
with the same date as was done already it will return response from the cache. Expiration is set for
one day. LRU is applied as well in here for 200 mb.

I have implemented apidocs as well running on /api/doc/ endpoint.


## Application steps
1. request is received and params are parsed. If there is any missing param user will be notified
2. checking from cache if there was already such request done with same params and if yes returning data from cache
3. if not the searching from cache each country to find if we have cached top airports of the country
4. if not making request to get country id
   - once I have country ID I am making request to get top 3 airports of the country
5. once I have both source and destination airports I am making request to each combination and trying to get best price
6. output of all the data are presented to the user in sorted by price manner

## Assumptions made
- Single adult with no children is making the request and therefor prices are given for single adult
- Economy class is chosen for flight search
- The requester does not need any bags with him :)
- I was not sure how often can top airports of a country change and therefor there is expiration of single day. This maybe could be changed for different amount of time
- Same for prices for the searched flights except expiration is for 3 days
- Currency used will be EUR
- I made it possible to have two stopovers otherwise I have received many 0 results.


## Problems
since I have two countries (source and destination) with full name I need to make two requests to get their respective IDs
and then another two requests to get top airports with received country IDs. This is 4 requests. The task is saying
that I need to return best price per source and destination airport. This made me do another 9 requests. I was trying to find
better way but simply comma separate to and from airports would not give me all the combinations. And I didn t want to assume
that if I will make output of 200 flights then all the combinations would be covered. I am sure there would be cases where it would
not be covered. I found param which said one for city. But there can be more than one airport per city and so our
top three can be in single city and therefor I would not receive correct result. I did not find any other param to make such request
in single request or at least less than 9 requests. For this reason I have received 429 too many requests error code from time to time.