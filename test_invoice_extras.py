#!/usr/bin/env python3
"""
Test script to verify invoice extras pricing calculations
"""

import json

def calculate_extras_price(extras_quantities):
    """
    Calculate extras price based on the pricing rules from app.py
    """
    price_table = {
        'Golden Imperial Lush': 15,
        'Golden Green Lush': 19,
        'Golden Natural 40mm': 17,
        'Golden Golf Turf': 22,
        'Golden Premium Turf': 20,
        'Peg (Upins/Nails)': 25 / 100,
        'Artificial Hedges': 10 / 0.25,
        'Black Pebbles': 18,
        'White Pebbles': 15,
        'Bamboo Products': {
            '2m': 40,
            '2.4m': 38,
            '1.8m': 38,
            'none': 0
        },
        'Adhesive Tape': 25
    }

    extras_price = 0.0
    extras_details = {}

    # Artificial Hedges
    ah_qty = extras_quantities.get('Artificial Hedges', 0)
    ah_price = price_table['Artificial Hedges'] * ah_qty
    extras_price += ah_price
    if ah_qty > 0:
        extras_details['Artificial Hedges'] = {'quantity': ah_qty, 'price': ah_price}

    # Fountain (manual price)
    fountain_qty = extras_quantities.get('Fountain', 0)
    fountain_price_per_item = extras_quantities.get('Fountain Price', 0)
    fountain_price = fountain_qty * fountain_price_per_item
    extras_price += fountain_price
    if fountain_qty > 0:
        extras_details['Fountain'] = {'quantity': fountain_qty, 'price': fountain_price}

    # Bamboo Products
    bamboo_qty = extras_quantities.get('Bamboo Products', 0)
    bamboo_size = extras_quantities.get('Bamboo Size', 'none')
    bamboo_unit_price = price_table['Bamboo Products'].get(bamboo_size, 0)
    bamboo_price = bamboo_qty * bamboo_unit_price
    extras_price += bamboo_price
    if bamboo_qty > 0 and bamboo_size != 'none':
        extras_details['Bamboo Products'] = {'bags': bamboo_qty, 'size': bamboo_size, 'price': bamboo_price}

    # Black Pebbles (price per bag)
    black_pebbles_qty = extras_quantities.get('Black Pebbles', 0)
    black_pebbles_price = black_pebbles_qty * price_table['Black Pebbles']
    extras_price += black_pebbles_price
    if black_pebbles_qty > 0:
        extras_details['Black Pebbles'] = {'bags': black_pebbles_qty, 'price': black_pebbles_price}

    # White Pebbles (price per bag)
    white_pebbles_qty = extras_quantities.get('White Pebbles', 0)
    white_pebbles_price = white_pebbles_qty * price_table['White Pebbles']
    extras_price += white_pebbles_price
    if white_pebbles_qty > 0:
        extras_details['White Pebbles'] = {'bags': white_pebbles_qty, 'price': white_pebbles_price}

    # Pegs (price per quantity)
    pegs_qty = extras_quantities.get('Pegs', 0)
    pegs_price = pegs_qty * price_table['Peg (Upins/Nails)']
    extras_price += pegs_price
    if pegs_qty > 0:
        extras_details['Pegs'] = {'quantity': pegs_qty, 'price': pegs_price}

    # Adhesive Tape (price per roll)
    adhesive_tape_qty = extras_quantities.get('Adhesive Tape', 0)
    adhesive_tape_price = adhesive_tape_qty * price_table['Adhesive Tape']
    extras_price += adhesive_tape_price
    if adhesive_tape_qty > 0:
        extras_details['Adhesive Tape'] = {'rolls': adhesive_tape_qty, 'price': adhesive_tape_price}

    return extras_price, extras_details

def test_extras_calculations():
    """
    Test various extras combinations to verify pricing
    """
    test_cases = [
        {
            'name': 'Single Black Pebbles Bag',
            'extras': {'Black Pebbles': 1},
            'expected_price': 18.0
        },
        {
            'name': 'Multiple Black Pebbles Bags',
            'extras': {'Black Pebbles': 3},
            'expected_price': 54.0
        },
        {
            'name': 'Single White Pebbles Bag',
            'extras': {'White Pebbles': 1},
            'expected_price': 15.0
        },
        {
            'name': 'Multiple White Pebbles Bags',
            'extras': {'White Pebbles': 4},
            'expected_price': 60.0
        },
        {
            'name': 'Single Adhesive Tape Roll',
            'extras': {'Adhesive Tape': 1},
            'expected_price': 25.0
        },
        {
            'name': 'Multiple Adhesive Tape Rolls',
            'extras': {'Adhesive Tape': 2},
            'expected_price': 50.0
        },
        {
            'name': 'Bamboo Products 2m - 1 bag',
            'extras': {'Bamboo Products': 1, 'Bamboo Size': '2m'},
            'expected_price': 40.0
        },
        {
            'name': 'Bamboo Products 2.4m - 2 bags',
            'extras': {'Bamboo Products': 2, 'Bamboo Size': '2.4m'},
            'expected_price': 76.0
        },
        {
            'name': 'Mixed Extras',
            'extras': {
                'Black Pebbles': 2,
                'White Pebbles': 1,
                'Adhesive Tape': 1,
                'Bamboo Products': 1,
                'Bamboo Size': '2m'
            },
            'expected_price': 18*2 + 15*1 + 25*1 + 40*1  # 36 + 15 + 25 + 40 = 116
        }
    ]

    print("Testing Invoice Extras Pricing Calculations")
    print("=" * 50)

    all_passed = True
    for test_case in test_cases:
        price, details = calculate_extras_price(test_case['extras'])
        expected = test_case['expected_price']

        if abs(price - expected) < 0.01:  # Allow for floating point precision
            status = "PASS"
        else:
            status = "FAIL"
            all_passed = False

        print(f"{test_case['name']}: {status}")
        print(f"  Expected: ${expected:.2f}")
        print(f"  Calculated: ${price:.2f}")
        if details:
            print(f"  Details: {json.dumps(details, indent=2)}")
        print()

    if all_passed:
        print("All tests PASSED! ✓")
    else:
        print("Some tests FAILED! ✗")

    return all_passed

if __name__ == "__main__":
    test_extras_calculations()
