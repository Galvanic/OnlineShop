#!/usr/bin/env python
# coding: utf-8

"""
Script to automate who owes what for an online shop (i.e. easily dividing
the bill).

Input:  A .txt file generated by copying the confirmation email content
        into a text file
        Asks who ordered which item
Output: Name of flatmate and their share of costs for that shop.

Future improvements:
- Yahoo Mail API to fetch shop receipt email automatically
- Makes guesses on whose item it is based on previous shop assignments

TODO: naming isn't quite there yet. Might want to explain here exactly
what each 'thing' represents.
"""

import re
import sys
import click
import datetime as dt
from collections import namedtuple
import sqlite3

from helper import ask, get_latest_file

RECEIPT_DIRECTORY = '../data/receipts/'
DB_FILE = '../data/onlineshop.db'

Purchase = namedtuple('Purchase', 'description, price, quantity')


def parse_receipt(receipt_filepath):
    """
    Finds all the ordered items (=purchases) in the receipt text (eg. the
    confirmation email for Ocado orders) using regular expressions.
    Returns a list of Purchases.
    """
    with open(receipt_filepath, 'rU') as f:
        ifile = f.read()
        purchases = re.findall(r'(^\d\d?) (.+?) £(\d\d?\.\d\d)', ifile, re.MULTILINE)

        delivery_date = re.search(r'Delivery date\s([\w\d ]+)', ifile)
        delivery_date = delivery_date.group(1)
        # format is WeekdayName MonthdayNumber MonthName
        delivery_date = dt.datetime.strptime(delivery_date, '%A %d %B')

        delivery_cost = re.search(r'Delivery\s.(\d\d?\.\d\d)', ifile)
        delivery_cost = float(delivery_cost.group(1))

        voucher = re.search(r'Voucher Saving\s.(-?\d\d?.\d\d)', ifile)
        voucher = float(voucher.group(1))

    purchases = [Purchase(description, float(price), int(quantity))
        for quantity, description, price in purchases]

    purchases.append(Purchase('Delivery costs', delivery_cost, 1))
    if voucher:
        purchases.append(Purchase('Voucher savings', voucher, 1))

    subtotal = sum([float(purchase.price) for purchase in purchases])
    total = subtotal + voucher + delivery_cost

    order_info = {
        'delivery date': delivery_date,
        'total': total,
    }

    return order_info, purchases


def assign_purchase(purchase):
    """
    Given an item, prints the quantity and description of the purchase, waits
    for user input and returns a list of purchasers' UIDs.
    User input is expected to be anything that would uniquely identify a
    flatmate (from the other flatmates). Multiple flatmates can be entered
    by seperating their UID by a space.
    """
    purchasers = ask('Who bought   {0.quantity} {0.description}   {1:<10}'.format(purchase, '?'), None, '')
    return purchasers.split()


def divide_order_bill(baskets):
    """
    Given a dictionary (flatmate UID: their cost share of each of
    their purchases), return a dictionary (flatmate UID: their total
    share of the order bill).

    TODO: need better name for this function
    """
    baskets = {flatmate:sum(purchases) for flatmate, purchases in baskets.items()}
    return baskets


def main(receipt_filepath):
    """"""
    if not receipt_filepath:
        receipt_filepath = get_latest_file(RECEIPT_DIRECTORY)

    order_info, purchases = parse_receipt(receipt_filepath)

    conn = sqlite3.connect(DB_FILE)
    curs = conn.cursor()

    try:
        ## assign all purchases
        print('\nEnter flatmate identifier(s) (either a name, initial(s) or number that you keep to later.')
        print('Seperate the identifiers by a space.\n')

        baskets = {}
        for index, purchase in enumerate(purchases, 1):
            if purchase.price == 0:
                continue

            cost_each = purchase.price / float(purchase.quantity)

            purchasers = assign_purchase(purchase)
            for flatmate in purchasers:
                if flatmate not in baskets:
                    baskets[flatmate] = [cost_each]
                else:
                    baskets[flatmate].append(cost_each)

        ## display how much each flatmate owes for the shop order
        for flatmate, owes in divide_order_bill(baskets).items():
            print('{} spent £{:.2f}'.format(flatmate, owes))

    except KeyboardInterrupt:
        pass

    finally:
        curs.close()

    return


@click.command()
@click.option('receipt_filepath', '-i', '--receipt',    default=None,
                                                        type=click.Path(exists=True),
                                                        help='Input filepath.')
def cli(*args, **kwargs):
    return main(*args, **kwargs)


if __name__ == '__main__':
    sys.exit(cli())