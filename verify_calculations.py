#!/usr/bin/env python3
"""
Verification script to check price calculations and categorizations
"""

import pandas as pd
import sys

def verify_calculations():
    """Verify all calculations in the results CSV are correct."""
    
    # Load the results
    df = pd.read_csv('inventory_analysis_results.csv')
    
    print("VERIFYING PRICE CALCULATIONS AND CATEGORIZATIONS")
    print("="*60)
    
    errors = []
    total_items = len(df)
    verified_items = 0
    
    for index, row in df.iterrows():
        item_id = row['Inventory ID']
        supplier_price = row['Supplier_Price']
        retail_price = row['Retail_Price']
        discount_percentage = row['Discount_Percentage']
        price_category = row['Price_Category']
        
        # Verify discount calculation
        if retail_price > 0:
            expected_discount = ((retail_price - supplier_price) / retail_price) * 100
        else:
            expected_discount = 0.0
        
        # Check discount calculation (allow small floating point differences)
        if abs(discount_percentage - expected_discount) > 0.1:
            errors.append(f"ERROR {item_id}: Discount calculation error")
            errors.append(f"   Expected: {expected_discount:.1f}%, Got: {discount_percentage:.1f}%")
            errors.append(f"   Supplier: ${supplier_price}, Retail: ${retail_price}")
            continue
        
        # Verify categorization
        if retail_price <= 0:
            expected_category = "No Price Found"
        elif discount_percentage >= 75:
            expected_category = "Good Price"
        elif discount_percentage >= 60:
            expected_category = "Okay Price"
        else:
            expected_category = "Bad Price"
        
        if price_category != expected_category:
            errors.append(f"ERROR {item_id}: Category error")
            errors.append(f"   Discount: {discount_percentage:.1f}%, Expected: {expected_category}, Got: {price_category}")
            continue
        
        verified_items += 1
    
    # Summary
    print(f"VERIFICATION RESULTS:")
    print(f"   Total items checked: {total_items}")
    print(f"   Items verified correct: {verified_items}")
    print(f"   Errors found: {len(errors) // 3 if errors else 0}")  # Each error is 3 lines
    
    if errors:
        print(f"\nERRORS FOUND:")
        for error in errors:
            print(error)
        return False
    else:
        print(f"\nALL CALCULATIONS AND CATEGORIZATIONS ARE CORRECT!")
        
        # Show some example verifications
        print(f"\nSAMPLE VERIFICATIONS:")
        
        # Show a few examples from each category
        good_items = df[df['Price_Category'] == 'Good Price'].head(3)
        okay_items = df[df['Price_Category'] == 'Okay Price'].head(3)
        bad_items = df[df['Price_Category'] == 'Bad Price'].head(3)
        no_price_items = df[df['Price_Category'] == 'No Price Found'].head(3)
        
        for category, items in [("Good Price (>75% off)", good_items), 
                               ("Okay Price (60-75% off)", okay_items),
                               ("Bad Price (<60% off)", bad_items),
                               ("No Price Found", no_price_items)]:
            if len(items) > 0:
                print(f"\n{category}:")
                for _, item in items.iterrows():
                    supplier = item['Supplier_Price']
                    retail = item['Retail_Price']
                    discount = item['Discount_Percentage']
                    
                    if retail > 0:
                        savings = retail - supplier
                        print(f"   {item['Inventory ID']}: ${supplier:.2f} -> ${retail:.2f} (Save ${savings:.2f}, {discount:.1f}% off)")
                    else:
                        print(f"   {item['Inventory ID']}: ${supplier:.2f} -> No retail price found")
        
        return True

def analyze_business_logic():
    """Analyze if the business logic makes sense."""
    
    df = pd.read_csv('inventory_analysis_results.csv')
    
    print(f"\nBUSINESS LOGIC ANALYSIS:")
    print("="*60)
    
    # Category breakdown
    categories = df['Price_Category'].value_counts()
    total = len(df)
    
    print(f"Category Distribution:")
    for category, count in categories.items():
        percentage = (count / total) * 100
        print(f"   {category}: {count} items ({percentage:.1f}%)")
    
    # Analyze discount ranges
    priced_items = df[df['Retail_Price'] > 0]
    if len(priced_items) > 0:
        print(f"\nDiscount Analysis (items with prices):")
        print(f"   Highest discount: {priced_items['Discount_Percentage'].max():.1f}%")
        print(f"   Lowest discount: {priced_items['Discount_Percentage'].min():.1f}%")
        print(f"   Average discount: {priced_items['Discount_Percentage'].mean():.1f}%")
        print(f"   Median discount: {priced_items['Discount_Percentage'].median():.1f}%")
    
    # Check for potential issues
    print(f"\nPotential Issues:")
    
    # Items with very low supplier prices but high retail prices (might be errors)
    suspicious = df[(df['Supplier_Price'] < 1.0) & (df['Retail_Price'] > 50.0)]
    if len(suspicious) > 0:
        print(f"   WARNING: {len(suspicious)} items with very low supplier price (<$1) but high retail price (>$50):")
        for _, item in suspicious.iterrows():
            print(f"      {item['Inventory ID']}: ${item['Supplier_Price']:.2f} vs ${item['Retail_Price']:.2f}")
    
    # Items with supplier price higher than retail (negative margin)
    negative_margin = df[df['Supplier_Price'] > df['Retail_Price']]
    negative_margin = negative_margin[negative_margin['Retail_Price'] > 0]  # Exclude no price items
    if len(negative_margin) > 0:
        print(f"   WARNING: {len(negative_margin)} items where supplier price > retail price:")
        for _, item in negative_margin.iterrows():
            print(f"      {item['Inventory ID']}: Supplier ${item['Supplier_Price']:.2f} > Retail ${item['Retail_Price']:.2f}")
    
    # Items with extremely high discounts (might be data errors)
    extreme_discounts = df[df['Discount_Percentage'] > 98.0]
    if len(extreme_discounts) > 0:
        print(f"   INFO: {len(extreme_discounts)} items with >98% discount (verify these are real):")
        for _, item in extreme_discounts.iterrows():
            print(f"      {item['Inventory ID']}: {item['Discount_Percentage']:.1f}% off (${item['Supplier_Price']:.2f} vs ${item['Retail_Price']:.2f})")
    
    if len(suspicious) == 0 and len(negative_margin) == 0:
        print("   No obvious data issues found!")

if __name__ == "__main__":
    success = verify_calculations()
    analyze_business_logic()
    
    if not success:
        sys.exit(1)
    
    print(f"\nVERIFICATION COMPLETE - All calculations are mathematically correct!") 