#!/usr/bin/env python3

import asyncio
import xml.etree.ElementTree as ET
import os
import json
from difflib import SequenceMatcher
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from menu_service import get_recipe_detail

app = Server("basic-mcp-server")

# Path to the XML file
XML_FILE = os.path.join(os.path.dirname(__file__), 'food_options.xml')

# In-memory cart storage (recipe_id -> item data with nutrients)
cart = {}

def parse_xml():
    """Parse the XML file and return the root element"""
    tree = ET.parse(XML_FILE)
    return tree.getroot()

def get_all_categories():
    """Extract all unique categories from the XML"""
    root = parse_xml()
    categories = set()
    for recipe in root.findall('RECIPE'):
        category = recipe.get('category', '')
        if category:
            categories.add(category)
    return sorted(list(categories))

def get_items_by_category(category_path):
    """Get all items matching a category path (supports partial matching)"""
    root = parse_xml()
    items = []
    for recipe in root.findall('RECIPE'):
        category = recipe.get('category', '')
        if category_path.lower() in category.lower() or category.lower().startswith(category_path.lower()):
            recipe_id = recipe.get('id', '')
            recipe_name = recipe.text.strip() if recipe.text else ''
            portion_size = recipe.get('portionsize', '')
            items.append({
                'id': recipe_id,
                'name': recipe_name,
                'category': category,
                'portion_size': portion_size
            })
    return items

def get_item_id_by_name(item_name):
    """Get the ID(s) of food item(s) by name using similarity scoring"""
    root = parse_xml()
    search_name = item_name.lower().strip()
    matches_with_scores = []
    
    for recipe in root.findall('RECIPE'):
        recipe_name = recipe.text.strip() if recipe.text else ''
        if not recipe_name:
            continue
        
        recipe_name_lower = recipe_name.lower()
        
        # Calculate similarity score using SequenceMatcher
        similarity = SequenceMatcher(None, search_name, recipe_name_lower).ratio()
        
        # Also try matching without common prefixes/suffixes
        recipe_clean = recipe_name_lower.replace('*', '').strip()
        similarity_clean = SequenceMatcher(None, search_name, recipe_clean).ratio()
        
        # Use the higher similarity score
        max_similarity = max(similarity, similarity_clean)
        
        if max_similarity > 0:  # Only include items with some similarity
            recipe_id = recipe.get('id', '')
            category = recipe.get('category', '')
            portion_size = recipe.get('portionsize', '')
            matches_with_scores.append({
                'id': recipe_id,
                'name': recipe_name,
                'category': category,
                'portion_size': portion_size,
                'similarity': max_similarity
            })
    
    # Sort by similarity score (highest first)
    matches_with_scores.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Return top matches (those with similarity > 0.3 or top 5)
    top_matches = [m for m in matches_with_scores if m['similarity'] > 0.3][:5]
    
    return top_matches if top_matches else matches_with_scores[:1]  # Return at least the best match

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="echo",
            description="Use this tool only when the user explicitly asks you to echo, repeat, or say back a specific message. Do not use this tool for regular conversation or greetings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to echo back",
                    }
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="get_categories",
            description="Retrieve all available food categories from the XML file. Returns a list of all unique category paths.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_items_by_category",
            description="Retrieve food items by category path. The category path can be a full path (e.g., 'Entrees:Meat:Beef') or partial (e.g., 'Beef' or 'Potatoes'). Returns items matching the category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_path": {
                        "type": "string",
                        "description": "The category path to search for (e.g., 'Entrees:Meat:Beef', 'Side Dishes:Potatoes', or just 'Beef')",
                    }
                },
                "required": ["category_path"],
            },
        ),
        Tool(
            name="get_item_id",
            description="Get the ID of a food item by searching for its name using similarity matching. Returns the best matching item(s) based on similarity score.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "The name of the food item to search for (e.g., 'Beef Stew', 'Gluten Free Roll, Hamburger Bun', 'Pizza'). The tool will find the most similar match.",
                    }
                },
                "required": ["item_name"],
            },
        ),
        Tool(
            name="get_recipe_detail",
            description="Get detailed information about a recipe by its ID. Returns recipe details including name, category, portion size, and optionally ingredients, methods, and nutritional information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "The recipe ID to get details for (e.g., '1032', '5765')",
                    },
                    "include_ingredients": {
                        "type": "boolean",
                        "description": "Whether to include ingredient information (default: false)",
                        "default": False,
                    },
                    "include_method": {
                        "type": "boolean",
                        "description": "Whether to include cooking method information (default: false)",
                        "default": False,
                    },
                    "include_ldas": {
                        "type": "boolean",
                        "description": "Whether to include LDA (Label Declaration Analysis) information (default: false)",
                        "default": False,
                    },
                },
                "required": ["recipe_id"],
            },
        ),
        Tool(
            name="add_to_cart",
            description="Add a food item to the cart by recipe ID. Fetches the recipe details with nutritional information and adds it to your cart. Returns confirmation with the item added.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "The recipe ID to add to cart (e.g., '1032', '5765')",
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Quantity of the item to add (default: 1)",
                        "default": 1,
                    },
                },
                "required": ["recipe_id"],
            },
        ),
        Tool(
            name="get_cart",
            description="Get the current cart contents with a summary of total macronutrients (calories, protein, carbs, fat, etc.). Returns all items in cart and their combined nutritional totals.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "echo":
        message = arguments.get("message", "")
        return [TextContent(type="text", text=f"Echo: {message}")]
    
    elif name == "get_categories":
        try:
            categories = get_all_categories()
            result = f"Found {len(categories)} categories:\n\n" + "\n".join(categories)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error retrieving categories: {str(e)}")]
    
    elif name == "get_items_by_category":
        try:
            category_path = arguments.get("category_path", "")
            if not category_path:
                return [TextContent(type="text", text="Error: category_path is required")]
            
            items = get_items_by_category(category_path)
            if not items:
                return [TextContent(type="text", text=f"No items found for category: {category_path}")]
            
            result = f"Found {len(items)} items in category '{category_path}':\n\n"
            for item in items[:10]:  # Limit to first 10 items
                result += f"- {item['name']} (ID: {item['id']}, Category: {item['category']}, Portion: {item['portion_size']})\n"
            
            if len(items) > 10:
                result += f"\n... and {len(items) - 10} more items"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error retrieving items: {str(e)}")]
    
    elif name == "get_item_id":
        try:
            item_name = arguments.get("item_name", "")
            if not item_name:
                return [TextContent(type="text", text="Error: item_name is required")]
            
            matches = get_item_id_by_name(item_name)
            if not matches:
                return [TextContent(type="text", text=f"No items found matching: {item_name}")]
            
            if len(matches) == 1:
                item = matches[0]
                result = f"Found best match for '{item_name}':\n\n"
                result += f"ID: {item['id']}\n"
                result += f"Name: {item['name']}\n"
                result += f"Category: {item['category']}\n"
                result += f"Portion Size: {item['portion_size']}\n"
                result += f"Similarity Score: {item['similarity']:.2%}"
            else:
                result = f"Found {len(matches)} best matches for '{item_name}':\n\n"
                for item in matches:
                    result += f"- {item['name']} (ID: {item['id']}, Similarity: {item['similarity']:.2%}, Category: {item['category']})\n"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error retrieving item ID: {str(e)}")]
    
    elif name == "get_recipe_detail":
        try:
            recipe_id = arguments.get("recipe_id", "")
            if not recipe_id:
                return [TextContent(type="text", text="Error: recipe_id is required")]
            
            include_ingredients = arguments.get("include_ingredients", False)
            include_method = arguments.get("include_method", False)
            include_ldas = arguments.get("include_ldas", False)
            
            # Call get_recipe_detail from menu_service
            recipe_data = get_recipe_detail(
                recipe_id,
                include_ingredients=include_ingredients,
                include_method=include_method,
                include_ldas=include_ldas,
            )
            
            # Format the result nicely
            result = ""
            
            # Extract and format key information
            if isinstance(recipe_data, dict) and 'RECIPE' in recipe_data:
                recipe = recipe_data['RECIPE']
                
                # Basic information
                if isinstance(recipe, dict):
                    # Get name first for heading
                    item_name = recipe.get('name') or recipe.get('value', 'Unknown')
                    recipe_id_val = recipe.get('id', recipe_id)
                    category = recipe.get('category', '')
                    portion_size = recipe.get('portionsize', '')
                    
                    # Format as heading
                    result += f"{item_name}\n\n"
                    
                    # Format details with proper spacing
                    result += f"ID: {recipe_id_val}\n"
                    if category:
                        result += f"Category: {category}\n"
                    if portion_size:
                        result += f"Portion Size: {portion_size}\n"
                    
                    # Description/Additional info if available
                    description = recipe.get('description', '')
                    if description:
                        result += f"\nDescription: {description}\n"
                    
                    # Additional details if available
                    if include_ingredients and 'ingredients' in recipe:
                        result += f"\nIngredients:\n{json.dumps(recipe.get('ingredients', {}), indent=2)}\n"
                    
                    if include_method and 'methods' in recipe:
                        result += f"\nCooking Methods:\n{json.dumps(recipe.get('methods', {}), indent=2)}\n"
                    
                    if include_ldas and 'ldas' in recipe:
                        result += f"\nLDA Information:\n{json.dumps(recipe.get('ldas', {}), indent=2)}\n"
                else:
                    result += json.dumps(recipe_data, indent=2)
            else:
                result += json.dumps(recipe_data, indent=2)
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error retrieving recipe details: {str(e)}")]
    
    elif name == "add_to_cart":
        try:
            recipe_id = str(arguments.get("recipe_id", ""))
            quantity = float(arguments.get("quantity", 1))
            
            if not recipe_id:
                return [TextContent(type="text", text="Error: recipe_id is required")]
            
            # Try to get recipe details from API with nutrients
            recipe_data = None
            recipe = None
            nutrients = {}
            
            try:
                recipe_data = get_recipe_detail(
                    recipe_id,
                    nutrients="all",  # Get all nutrients
                    rounding="raw"
                )
                
                # Check for API errors
                if recipe_data and 'STATUS' in recipe_data:
                    status = recipe_data['STATUS']
                    if isinstance(status, dict) and status.get('success') != '1':
                        error = status.get('ERROR', {})
                        if isinstance(error, dict) and error.get('number'):
                            # API error - fall back to XML data
                            recipe_data = None
                
                # Handle both RECIPE (singular) and RECIPES (plural) responses
                if recipe_data and 'RECIPE' in recipe_data:
                    recipe = recipe_data['RECIPE']
                elif recipe_data and 'RECIPES' in recipe_data:
                    recipes_data = recipe_data['RECIPES']
                    # If RECIPES is a dict, try to find the actual recipe data
                    if isinstance(recipes_data, dict):
                        # Check if there's a RECIPE key inside RECIPES
                        if 'RECIPE' in recipes_data:
                            recipe = recipes_data['RECIPE']
                        else:
                            # Use RECIPES as the recipe data
                            recipe = recipes_data
                    else:
                        recipe = recipes_data
            except Exception as e:
                # API call failed - fall back to XML data
                recipe_data = None
                recipe = None
            
            # Fall back to XML data if API failed
            if not recipe:
                root = parse_xml()
                xml_recipe = root.find(f"./RECIPE[@id='{recipe_id}']")
                if xml_recipe is None:
                    return [TextContent(type="text", text=f"Error: Could not find recipe with ID {recipe_id}")]
                
                # Extract from XML
                item_name = xml_recipe.text.strip() if xml_recipe.text else 'Unknown'
                portion_size = xml_recipe.get('portionsize', '')
                category = xml_recipe.get('category', '')
            else:
                # Extract recipe information from API response
                item_name = recipe.get('name') or recipe.get('value', 'Unknown')
                portion_size = recipe.get('portionsize', '')
                category = recipe.get('category', '')
                
                # Extract nutrients from API response
                # Check for nutrients in various possible locations
                nutrients_data = None
                if isinstance(recipe, dict):
                    # Check for nutrients in recipe dict
                    if 'nutrients' in recipe:
                        nutrients_data = recipe['nutrients']
                    elif 'NUTRIENTS' in recipe:
                        nutrients_data = recipe['NUTRIENTS']
                    # Also check in parent RECIPES structure
                    if not nutrients_data and recipe_data and 'RECIPES' in recipe_data:
                        recipes_data = recipe_data['RECIPES']
                        if isinstance(recipes_data, dict) and 'NUTRIENTS' in recipes_data:
                            nutrients_data = recipes_data['NUTRIENTS']
                
                # Parse nutrients data
                if nutrients_data:
                    if isinstance(nutrients_data, dict):
                        # If it's a dict, extract values directly
                        for key, value in nutrients_data.items():
                            if key != 'NUTRIENTS':  # Skip metadata strings
                                try:
                                    nutrients[key] = float(value) if value else 0
                                except (ValueError, TypeError):
                                    nutrients[key] = 0
                    elif isinstance(nutrients_data, list):
                        # If it's a list of nutrient objects
                        for nutrient in nutrients_data:
                            if isinstance(nutrient, dict):
                                nutrient_name = nutrient.get('name', '')
                                nutrient_value = nutrient.get('value', 0)
                                if nutrient_name:
                                    try:
                                        nutrients[nutrient_name] = float(nutrient_value) if nutrient_value else 0
                                    except (ValueError, TypeError):
                                        nutrients[nutrient_name] = 0
                    elif isinstance(nutrients_data, str):
                        # If it's a string (metadata), nutrients aren't available
                        # This is just a list of available nutrients, not actual values
                        nutrients = {}
            
            # Store base nutrients (per unit) for this recipe
            base_nutrients = nutrients.copy()
            
            # Store in cart (multiply nutrients by quantity)
            cart_item = {
                'recipe_id': recipe_id,
                'name': item_name,
                'category': category,
                'portion_size': portion_size,
                'quantity': quantity,
                'base_nutrients': base_nutrients,  # Store per-unit nutrients
                'nutrients': {k: v * quantity for k, v in nutrients.items()}  # Total nutrients
            }
            
            # If item already in cart, update quantity and nutrients
            if recipe_id in cart:
                existing_quantity = cart[recipe_id]['quantity']
                new_quantity = existing_quantity + quantity
                cart[recipe_id]['quantity'] = new_quantity
                # Use existing base_nutrients if available, otherwise use new ones
                existing_base = cart[recipe_id].get('base_nutrients', base_nutrients)
                cart[recipe_id]['base_nutrients'] = existing_base
                # Recalculate total nutrients based on base nutrients and new quantity
                cart[recipe_id]['nutrients'] = {k: v * new_quantity for k, v in existing_base.items()}
            else:
                cart[recipe_id] = cart_item
            
            result = f"Added to cart ({quantity}x):\n"
            result += f"Name: {item_name}\n"
            result += f"ID: {recipe_id}\n"
            result += f"Portion Size: {portion_size}\n"
            if nutrients:
                result += f"\nNutrients (per {portion_size}):\n"
                for nutrient_name, nutrient_value in list(nutrients.items())[:10]:  # Show first 10
                    result += f"  {nutrient_name}: {nutrient_value}\n"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error adding to cart: {str(e)}")]
    
    elif name == "get_cart":
        try:
            if not cart:
                return [TextContent(type="text", text="Your cart is empty.")]
            
            # Calculate totals
            total_nutrients = {}
            items_list = []
            
            for recipe_id, item in cart.items():
                items_list.append(f"- {item['name']} (ID: {item['recipe_id']}, Qty: {item['quantity']}, Portion: {item['portion_size']})")
                
                # Sum up nutrients
                for nutrient_name, nutrient_value in item.get('nutrients', {}).items():
                    if nutrient_name in total_nutrients:
                        total_nutrients[nutrient_name] += nutrient_value
                    else:
                        total_nutrients[nutrient_name] = nutrient_value
            
            result = f"Cart Summary ({len(cart)} items):\n\n"
            result += "Items:\n"
            result += "\n".join(items_list)
            
            result += "\n\nTotal Macronutrients:\n"
            # Common macro nutrients to display
            macro_names = ['Calories', 'Protein', 'Carbohydrates', 'Total Fat', 'Saturated Fat', 'Fiber', 'Sodium']
            
            for macro in macro_names:
                # Try different variations of the name
                found = False
                for nutrient_name, value in total_nutrients.items():
                    if macro.lower() in nutrient_name.lower() or nutrient_name.lower() in macro.lower():
                        result += f"  {macro}: {value:.2f}\n"
                        found = True
                        break
                
                if not found:
                    # Try exact match
                    if macro in total_nutrients:
                        result += f"  {macro}: {total_nutrients[macro]:.2f}\n"
            
            # Show other nutrients if available
            other_nutrients = {k: v for k, v in total_nutrients.items() 
                              if not any(macro.lower() in k.lower() for macro in macro_names)}
            if other_nutrients:
                result += "\nOther Nutrients:\n"
                for nutrient_name, value in list(other_nutrients.items())[:10]:  # Limit to 10
                    result += f"  {nutrient_name}: {value:.2f}\n"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error retrieving cart: {str(e)}")]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

