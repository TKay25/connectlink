"""
AI Product Category Classifier
Automatically determines product category and subcategory based on product name
"""

from fuzzywuzzy import fuzz, process
import json
from typing import Dict, Tuple, List

class ProductCategoryClassifier:
    """
    Classifies products into categories and subcategories using keyword matching + fuzzy logic
    """
    
    def __init__(self):
        """Initialize with category/subcategory mapping and product keywords"""
        
        self.category_mapping = {
            "Gas Products": ["Gas Tanks", "Gas Regulators"],
            "Building Materials": ["Brickforce", "DPC", "Plastic", "Wire Mesh", "Edge Strips", 
                                  "Barbed Wire", "Rope", "Sand Paper"],
            "Electrical": ["Cables", "Conduit", "Couplings", "Cover Boxes", "Round Boxes", 
                          "Switches", "Sockets", "Breakers", "Magnetic Breakers", "Meter Boxes", 
                          "Insulation Tape", "Lampholders", "LED Lights", "Earth Rods", 
                          "Cable Terminals", "Gang Switches", "Cooker Units"],
            "Measuring Tools": ["Tape Measures", "Spirit Level", "Straight Edge"],
            "Plumbing": ["Pipes", "Pipe Fittings", "Bends", "Tees", "Traps", "Flexi Pipes", 
                        "Silicone", "Hose Pipe", "Angle Valves", "Saddles", "Glass Pipes"],
            "General Tools": ["Hammers", "Claw Hammer", "Chasing Hammer", "Hammer Heads", 
                             "Shovel", "Spade", "Screwdrivers", "Allen Keys", "Spanners", 
                             "Shifting Spanner", "Pliers", "Side Cutters", "Cutters", "Saws", 
                             "Hack Saws", "Drill Bits", "Concrete Drill Bits", "Flicker Machine", 
                             "Torque Wrench", "Wheel Barrows"],
            "Finishing & Painting Tools": ["Paint Brushes", "Rolling Brush", "Flicker Brush", 
                                          "Trowels", "Floats", "Wooden Float", "Jointers", "Wood Chisel", "Nylon Brush"],
            "Paint & Coatings": ["Paint", "Spray Paint", "Primer", "Wood Stain", "Masonry Paint", "Cement Paint"],
            "Hardware": ["Door Locks", "Lock Sets", "Flash Doors", "White Button Doors", "Boxes", 
                        "Flush Boxes", "Hinges", "Handles", "Metal Clamps", "Fischer Plugs", 
                        "Security Sticks"],
            "Fasteners": ["Screws", "Nails", "Wire Nails", "Bolts", "Basin Bolts", "Washers", 
                         "Nuts", "Anchors", "Epoxy Steel"],
            "Safety Equipment": ["Gloves", "Glass Gloves", "PVC Gloves", "Goggles", "Masks", 
                                "Hard Hats"],
            "Cleaning Supplies": ["Brooms", "Square Brooms", "Flat Brooms", "Mops", "Rakes"],
            "Kitchen & Bathroom": ["Shower Mixers", "Basin", "Pan Connectors", "S-Trap", "P-Trap"],
            "Appliances": ["Stove", "Oven"],
            "Cookware & Pots": ["Garden Pots", "Gainstar Pots", "Maifam Pots", "Cast Iron Pots"],
            "Blankets & Comforters": ["Light Blanket", "Medium Blanket", "Heavy Blanket", 
                                      "Li View Comforters"],
            "Pest Control": ["Termite Poison"],
            "Belts & Straps": ["Truck Belts"],
            "Aluminium": ["Aluminium", "Aluminium Saws"],
            "Electrical Switches & Controls": ["MCB Switch", "Dimmer Switch", "Motion Sensor", 
                                               "Tripper Armature", "Gang Switch", "Electrical Switch"],
            "Electrical Components": ["Cable Gland", "Armature Coil", "Metal Gland", "Tripper", 
                                      "2-head Metal Gland", "Lead Seal"],
            "Building Board & Sheeting": ["Plaster Board", "Bakelite Sheet", "Door Frame", "Profile Board", 
                                          "Cover Board", "Cement Board"],
            "Plumbing Accessories": ["Pipe Bending Spring", "Lead Seal", "Compression Joint", 
                                     "Copper Pipe", "Paper Joint", "Hacksaw Frame", "Hacksaw Blade"],
            "Equipment & Machinery": ["JCB Jockey", "JCB JF-5", "Pendant Box"],
            "Other": ["Other"]
        }
        
        # Keywords that help identify categories
        self.category_keywords = {
            "Gas Products": ["gas", "tank", "lpg", "propane", "regulator", "valve"],
            "Building Materials": ["brick", "concrete", "cement", "dpc", "plastic sheet", "mesh", 
                                  "wire", "rope", "sand paper", "sandpaper"],
            "Electrical": ["cable", "wire", "conduit", "switch", "socket", "breaker", "meter", 
                          "lamp", "led", "light", "bulb", "earth", "terminal"],
            "Measuring Tools": ["tape", "measure", "level", "ruler", "straight edge"],
            "Plumbing": ["pipe", "fitting", "bend", "trap", "valve", "hose", "silicone", "flexi"],
            "General Tools": ["hammer", "shovel", "spade", "screwdriver", "wrench", "plier", 
                             "cutter", "saw", "drill", "bit", "key", "wrench"],
            "Finishing & Painting Tools": ["brush", "roller", "trowel", "float", "jointer", "smoothing"],
            "Paint & Coatings": ["paint", "primer", "varnish", "spray paint", "coating"],
            "Hardware": ["lock", "door", "hinge", "handle", "clamp", "plug", "box"],
            "Fasteners": ["screw", "nail", "bolt", "washer", "nut", "anchor", "epoxy"],
            "Safety Equipment": ["glove", "goggle", "mask", "hat", "protection", "ppe"],
            "Cleaning Supplies": ["broom", "mop", "rake", "sweep", "clean"],
            "Kitchen & Bathroom": ["kitchen", "bathroom", "shower", "basin", "tap", "mixer"],
            "Appliances": ["stove", "oven", "cooker", "electric"],
            "Cookware & Pots": ["pot", "pan", "cookware", "container"],
            "Blankets & Comforters": ["blanket", "comforter", "quilt", "bedding"],
            "Pest Control": ["pest", "poison", "termite", "insect"],
            "Belts & Straps": ["belt", "strap", "tie"],
            "Aluminium": ["aluminium", "aluminum", "alloy"]
        }
    
    def classify_product(self, product_name: str, description: str = "") -> Dict:
        """
        Classify a product into category and subcategory
        
        Args:
            product_name (str): Name of the product
            description (str): Optional product description
        
        Returns:
            Dict with keys:
                - category: Main category
                - subcategory: Sub-category
                - confidence: Confidence score (0-100)
                - alternatives: List of alternative suggestions
        """
        
        # Combine product name and description for analysis
        full_text = f"{product_name} {description}".lower()
        
        # Try direct subcategory match first (highest priority)
        direct_match = self._find_direct_subcategory_match(product_name)
        if direct_match:
            return {
                "category": direct_match[0],
                "subcategory": direct_match[1],
                "confidence": 95,
                "method": "exact_match"
            }
        
        # Try keyword-based category matching
        category_scores = self._score_categories_by_keywords(full_text)
        
        if not category_scores:
            # Fallback to "Other" category
            return {
                "category": "Other",
                "subcategory": "Other",
                "confidence": 20,
                "method": "fallback"
            }
        
        # Get top category
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        
        # Get best subcategory from fuzzy matching
        best_subcategory = self._find_best_subcategory(
            product_name, 
            self.category_mapping[best_category]
        )
        
        # Get alternatives (other top categories)
        sorted_scores = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        alternatives = [cat for cat, score in sorted_scores[1:4] if score > 20]
        
        return {
            "category": best_category,
            "subcategory": best_subcategory,
            "confidence": min(int(best_score), 99),
            "alternatives": alternatives,
            "method": "keyword_matching"
        }
    
    def _find_direct_subcategory_match(self, product_name: str) -> Tuple[str, str] or None:
        """
        Try to find exact or very close match for the product in subcategories
        """
        product_lower = product_name.lower()
        
        for category, subcategories in self.category_mapping.items():
            for subcategory in subcategories:
                # Direct match
                if product_lower == subcategory.lower():
                    return (category, subcategory)
                
                # Partial match (product name contains subcategory)
                if subcategory.lower() in product_lower or product_lower in subcategory.lower():
                    ratio = fuzz.token_sort_ratio(product_lower, subcategory.lower())
                    if ratio > 85:
                        return (category, subcategory)
        
        return None
    
    def _score_categories_by_keywords(self, text: str) -> Dict[str, float]:
        """
        Score categories based on keyword matches in text
        """
        scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 10  # Each keyword match adds 10 points
                    # Extra points if keyword appears at start
                    if text.startswith(keyword):
                        score += 5
            
            scores[category] = score
        
        return {cat: score for cat, score in scores.items() if score > 0}
    
    def _find_best_subcategory(self, product_name: str, subcategories: List[str]) -> str:
        """
        Find best matching subcategory using fuzzy string matching
        """
        if not subcategories:
            return "Other"
        
        matches = process.extract(product_name, subcategories, limit=1, scorer=fuzz.token_sort_ratio)
        
        if matches and matches[0][1] > 40:
            return matches[0][0]
        
        # Return first subcategory if no good match
        return subcategories[0]
    
    def get_suggestions_for_partial_name(self, partial_name: str, limit: int = 3) -> List[Dict]:
        """
        Get category suggestions as user types product name (for autocomplete)
        
        Returns list of suggestions with categories
        """
        if len(partial_name) < 2:
            return []
        
        suggestions = []
        
        # Get all subcategories
        all_subcategories = []
        for category, subs in self.category_mapping.items():
            for sub in subs:
                all_subcategories.append((category, sub))
        
        # Fuzzy match against all subcategories
        for category, subcategory in all_subcategories:
            ratio = fuzz.ratio(partial_name.lower(), subcategory.lower())
            if ratio > 40:
                suggestions.append({
                    "name": subcategory,
                    "category": category,
                    "subcategory": subcategory,
                    "match_score": ratio
                })
        
        # Sort by match score and return top N
        suggestions.sort(key=lambda x: x['match_score'], reverse=True)
        return suggestions[:limit]


# Initialize classifier instance
classifier = ProductCategoryClassifier()


def add_dynamic_category(category_name: str, subcategory_items: List[str]) -> bool:
    """
    Dynamically add a new category to the classifier
    
    Usage:
        add_dynamic_category("Smart Home", ["Smart Lights", "Smart Switches"])
    
    Returns:
        bool: True if successfully added, False otherwise
    """
    try:
        classifier.category_mapping[category_name] = subcategory_items
        # Add keywords for the new category (using first subcategory as keywords)
        classifier.category_keywords[category_name] = [
            word.lower() for subcategory in subcategory_items[:2]
            for word in subcategory.split()
        ]
        return True
    except Exception as e:
        print(f"Error adding dynamic category: {str(e)}")
        return False


def classify_product(product_name: str, description: str = "") -> Dict:
    """
    Public function to classify a product
    
    Usage:
        result = classify_product("Titanium Screwdriver Set")
        print(result)
        # Output: {
        #    'category': 'General Tools',
        #    'subcategory': 'Screwdrivers',
        #    'confidence': 92,
        #    'method': 'exact_match'
        # }
    """
    return classifier.classify_product(product_name, description)


def get_category_suggestions(partial_name: str) -> List[Dict]:
    """
    Get autocomplete suggestions as user types
    
    Usage:
        suggestions = get_category_suggestions("paint")
        # Returns matching paint-related products with categories
    """
    return classifier.get_suggestions_for_partial_name(partial_name)


# Test the classifier
if __name__ == "__main__":
    test_products = [
        ("Titanium Screwdriver", "Phillips head, magnetic tip"),
        ("LED Bulb 60W", "Warm white, energy efficient"),
        ("Chrome Door Lock", "Heavy duty, security lock"),
        ("Paint Roller 4 inch", "Professional nap roller"),
        ("Electrical Cable 2.5mm", "2-core copper wire"),
        ("Mystery Product X", ""),
    ]
    
    print("=" * 60)
    print("AI Product Category Classifier - Test Results")
    print("=" * 60)
    
    for product_name, description in test_products:
        result = classify_product(product_name, description)
        print(f"\n📦 Product: {product_name}")
        if description:
            print(f"   Description: {description}")
        print(f"   ✅ Category: {result['category']}")
        print(f"   ✅ Sub-Category: {result['subcategory']}")
        print(f"   📊 Confidence: {result['confidence']}%")
        if result.get('alternatives'):
            print(f"   🔄 Alternatives: {', '.join(result['alternatives'][:2])}")
    
    print("\n" + "=" * 60)
    print("Category Autocomplete Test")
    print("=" * 60)
    
    test_queries = ["screw", "paint", "elec"]
    for query in test_queries:
        suggestions = get_category_suggestions(query)
        print(f"\n🔍 Query: '{query}'")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion['name']} ({suggestion['category']}) - {suggestion['match_score']}%")
