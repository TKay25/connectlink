"""
Test inventory coverage against AI classifier
Checks which products from the inventory list can be classified
"""

from ai_classifier import classify_product

# Full product list from the attachment (extracted from image)
inventory_products = [
    "Big ant tree",
    "Big ant",
    "Tape",
    "LED SPQ",
    "Led ring",
    "Light fixture",
    "Screwdriver",
    "Jcb jockey",
    "Jcb jf-5",
    "1.5 head cables",
    "1.5 twinline cables",
    "2.0 hard plastic",
    "2.5 hard plastic",
    "Electrical cable",
    "Telephone panels",
    "Telephone socket",
    "Junction box",
    "Electrical outlet",
    "MCB switch",
    "Gang switch",
    "Cooker unit",
    "Round box",
    "Cover board",
    "Profile board",
    "Primer",
    "Paper joint",
    "2 head metal gland",
    "Cable gland",
    "Trunk tail",
    "Pendant box",
    "Tripper armature",
    "Armature coil",
    "Switch board",
    "Silicon sealant",
    "Silicone sealant",
    "Door frame",
    "Cement paint",
    "Masonry paint",
    "Brick cement",
    "Paint brush",
    "Nylon brush",
    "Wood chisel",
    "Hacksaw frame",
    "Hacksaw blade",
    "2 inch pipe",
    "1 inch bends",
    "3 inch tees",
    "Flexi hose pipe",
    "Copper pipe",
    "Lead seal",
    "Basin trap",
    "Bakelite sheet",
    "Wood stain",
    "Sealant 250ml",
    "Door bell",
    "Dimmer switch",
    "Motion sensor",
    "Pipe bending spring",
    "Plaster board"
]

# Analyze coverage
print("=" * 80)
print("INVENTORY COVERAGE ANALYSIS")
print("=" * 80)

results = {
    "high_confidence": [],  # 80+%
    "medium_confidence": [],  # 50-79%
    "low_confidence": [],  # <50%
    "needs_new_category": []
}

for product in inventory_products:
    classification = classify_product(product)
    confidence = classification.get('confidence', 0)
    category = classification.get('category', 'Unknown')
    subcategory = classification.get('subcategory', 'Unknown')
    
    result_entry = {
        'product': product,
        'category': category,
        'subcategory': subcategory,
        'confidence': confidence,
        'method': classification.get('method', 'unknown')
    }
    
    if confidence >= 80:
        results["high_confidence"].append(result_entry)
    elif confidence >= 50:
        results["medium_confidence"].append(result_entry)
    elif category == "Other":
        results["needs_new_category"].append(result_entry)
    else:
        results["low_confidence"].append(result_entry)

# Print results
print(f"\n✅ HIGH CONFIDENCE (80-100%): {len(results['high_confidence'])} products")
print("-" * 80)
for item in results["high_confidence"]:
    print(f"  ✓ {item['product']:<40} → {item['category']:<25} [{item['confidence']}%]")

print(f"\n⚠️  MEDIUM CONFIDENCE (50-79%): {len(results['medium_confidence'])} products")
print("-" * 80)
for item in results["medium_confidence"]:
    print(f"  ⚠ {item['product']:<40} → {item['category']:<25} [{item['confidence']}%]")

print(f"\n❌ LOW CONFIDENCE (<50%): {len(results['low_confidence'])} products")
print("-" * 80)
for item in results["low_confidence"]:
    print(f"  ✗ {item['product']:<40} → {item['category']:<25} [{item['confidence']}%]")

print(f"\n🔴 NEEDS NEW CATEGORY: {len(results['needs_new_category'])} products")
print("-" * 80)
for item in results["needs_new_category"]:
    print(f"  ⚠ {item['product']:<40} → {item['category']:<25} [{item['confidence']}%]")

# Summary statistics
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
total = len(inventory_products)
covered_high = len(results["high_confidence"])
covered_medium = len(results["medium_confidence"])
covered_low = len(results["low_confidence"])
needs_new = len(results["needs_new_category"])

print(f"Total Products:           {total}")
print(f"Covered (High):           {covered_high} ({covered_high*100//total}%)")
print(f"Covered (Medium):         {covered_medium} ({covered_medium*100//total}%)")
print(f"Covered (Low):            {covered_low} ({covered_low*100//total}%)")
print(f"Need New Categories:      {needs_new} ({needs_new*100//total}%)")
print(f"TOTAL COVERAGE:           {(covered_high+covered_medium)*100//total}% (High+Medium)")

# Suggest new categories needed
print("\n" + "=" * 80)
print("SUGGESTED NEW CATEGORIES")
print("=" * 80)

categories_to_add = set()
for item in results["needs_new_category"]:
    product_lower = item['product'].lower()
    
    # Auto-suggest categories based on keywords
    if any(word in product_lower for word in ['switch', 'dimmer', 'motion', 'sensor']):
        categories_to_add.add("Electrical Controls")
    if any(word in product_lower for word in ['paint', 'stain', 'primer', 'varnish', 'coating']):
        categories_to_add.add("Paint & Dyes")
    if any(word in product_lower for word in ['brush', 'nylon', 'chisel']):
        categories_to_add.add("Hand Finishing Tools")
    if any(word in product_lower for word in ['board', 'plaster', 'sheet', 'frame']):
        categories_to_add.add("Building Components")
    if any(word in product_lower for word in ['bakelite', 'handle', 'grip']):
        categories_to_add.add("Electrical Accessories")
    if any(word in product_lower for word in ['gland', 'armature', 'coil']):
        categories_to_add.add("Electrical Components")
    if any(word in product_lower for word in ['bell', 'chime']):
        categories_to_add.add("Electrical Fixtures")

if categories_to_add:
    print("Recommended new categories:")
    for i, category in enumerate(sorted(categories_to_add), 1):
        print(f"  {i}. {category}")
else:
    print("  All products can be covered with current categories!")
