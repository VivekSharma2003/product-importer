#!/usr/bin/env python3
"""Generate a large CSV file for testing the import functionality."""

import csv
import random
import string
import argparse
from pathlib import Path


def generate_sku():
    """Generate a random SKU."""
    prefix = random.choice(['PROD', 'ITEM', 'SKU', 'WIDGET', 'GADGET', 'TOOL'])
    number = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}-{number}"


def generate_name():
    """Generate a random product name."""
    adjectives = ['Premium', 'Basic', 'Pro', 'Elite', 'Standard', 'Deluxe', 
                  'Ultra', 'Smart', 'Classic', 'Modern', 'Compact', 'Portable']
    nouns = ['Widget', 'Gadget', 'Tool', 'Device', 'Accessory', 'Component',
             'Module', 'Unit', 'Kit', 'Set', 'Pack', 'Bundle']
    suffix = random.choice(['', ' Plus', ' Max', ' Mini', ' X', ' Pro', ' Lite'])
    return f"{random.choice(adjectives)} {random.choice(nouns)}{suffix}"


def generate_description():
    """Generate a random product description."""
    templates = [
        "High-quality {} for professional use.",
        "Perfect {} for everyday needs.",
        "Innovative {} with advanced features.",
        "Reliable {} built to last.",
        "Modern {} with sleek design.",
        "Versatile {} for multiple applications.",
        "Premium {} with exceptional performance.",
    ]
    product_types = ['product', 'solution', 'item', 'tool', 'device']
    return random.choice(templates).format(random.choice(product_types))


def generate_csv(output_path: str, num_rows: int):
    """Generate a CSV file with the specified number of rows."""
    print(f"Generating {num_rows:,} products...")
    
    used_skus = set()
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['sku', 'name', 'description', 'price', 'quantity'])
        writer.writeheader()
        
        for i in range(num_rows):
            # Generate unique SKU
            sku = generate_sku()
            while sku in used_skus:
                sku = generate_sku()
            used_skus.add(sku)
            
            writer.writerow({
                'sku': sku,
                'name': generate_name(),
                'description': generate_description(),
                'price': round(random.uniform(9.99, 999.99), 2),
                'quantity': random.randint(0, 1000)
            })
            
            if (i + 1) % 50000 == 0:
                print(f"  Generated {i + 1:,} products...")
    
    file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"Done! Generated {num_rows:,} products")
    print(f"File: {output_path}")
    print(f"Size: {file_size_mb:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description='Generate a large CSV file for testing')
    parser.add_argument('-n', '--num-rows', type=int, default=10000,
                        help='Number of rows to generate (default: 10000)')
    parser.add_argument('-o', '--output', type=str, default='test_products.csv',
                        help='Output file path (default: test_products.csv)')
    
    args = parser.parse_args()
    generate_csv(args.output, args.num_rows)


if __name__ == '__main__':
    main()
