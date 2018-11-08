#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pandas import to_datetime
import datetime
import argparse
import sys


def get_datetime_from_args(date_time):
    """
    Datetime strings from the commandline can come in a list, so we need to
    join it back in as a single string for pandas to handle it.
    """
    if type(date_time) == list:
        date_time = " ".join(date_time)

    if type(date_time) == str:
        date_time = to_datetime(date_time)
    else:
        date_time = date_time

    return date_time


def handle_year_stradling(date_time):
    """
    Deals with the scenario of the water year starting in
    10/1/N  and ending in 10/1/N+1, assumes that the water year is asssociated
    to the bulk of time at the year which is N+1

    Depending on the time, will return the appropiate year for the starting
    point
    """

    if date_time.month < 10:
        year = date_time.year-1
    else:
        year = date_time.year

    return year

def calculate_end_of_day(date_time):
    """
    Calculates the end of the day given date
    """
    date_time = datetime.datetime(year=date_time.year, month=date_time.month,
                                                   day=date_time.day,
                                                   hour=23)
    return date_time


def calculate_date_from_wyhr(wyhr, year):
    """
    Takes in the integer of water year hours and an integer year and
    returns the date
    """

    start = datetime.datetime(year=year-1, month=10, day=1)

    delta = datetime.timedelta(hours = wyhr)
    return start+delta


def calculate_wyhr_from_date(date_time):
    """
    Takes in the string of the datetime and returns an integer of the water year
    hour.

    Args:

        date_time: string or date time objec to use for calculating the water year
    """

    year = handle_year_stradling(date_time)

    start = datetime.datetime(year=year, month=10, day=1)

    delta = date_time - start

    return int((delta.total_seconds())/3600)


def main():
    parser = argparse.ArgumentParser(description="Converts dates and water year hour")
    parser.add_argument('convertable', nargs='+', default=None,
                        help="Receives either a datetime or wyhr and "
                        "infers automatically")

    parser.add_argument("--date","-d", type=str, dest='date',nargs='+',
                    help="String of date time to convert to water year hour")
    parser.add_argument('--wyhr', dest='wyhr', type=int,
                        help="Integer of water year hours")
    parser.add_argument('--year','-y', dest='year', type=int,
                        help="Integer of year, required when converting from"
                             " wyhr")
    parser.add_argument('--eod', dest='eod', action='store_true',
                        help="Flag for calculating the end of the day wyhr")
    args = parser.parse_args()

    # Snag todays date
    today = datetime.datetime.now()

    # Print a header
    msg = "WYHR Conversion Utility:"
    hdr = "=" * len(msg)
    print("\n")
    print(msg)
    print(hdr)

    # Try to infer the users input if no args are provided.
    if args.convertable != None:

        # Check for wyhr
        try:
            args.wyhr = int(" ".join(args.convertable))

        except:
            args.wyhr = None

        # Check for datetime
        if args.wyhr == None:
            try:
                date = get_datetime_from_args(" ".join(args.convertable))
                args.date = args.convertable

            except Exception as e:
                print("\nERROR: Could not distinguish argument as a WYHR or a"
                      " datetime.\nException: {}\n".format(e))
                sys.exit()

    # Convert from date specified
    if args.date != None:
        date = get_datetime_from_args(args.date)
        from_date = True

    # Convert from water year hour
    elif args.wyhr != None and args.year != None :
        wyhr = args.wyhr
        year=args.year
        from_date = False

    # Assume water year conversion from this year
    elif args.wyhr != None and args.year == None:
        wyhr = args.wyhr
        year = today.year
        from_date = False

    # Assume calculate wyhr from today
    else:
        date = today
        from_date = True

    # Perform the final calculation
    if from_date:
        # Force the end of the day
        if args.eod:
            date = calculate_end_of_day(date)

        wyhr = calculate_wyhr_from_date(date)

    else:
        date = calculate_date_from_wyhr(wyhr, year)


    print("Date: {0}".format(date.strftime("%Y-%m-%d %H:00")))
    print("WYHR: {0}".format(wyhr))
    print('\n')

if __name__ == '__main__':
    main()
