#!/usr/bin/env python3

import asyncio
import xml.etree.ElementTree as ET
import os
from difflib import SequenceMatcher
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("basic-mcp-server")

# Path to the XML file
XML_FILE = os.path.join(os.path.dirname(__file__), 'food_options.xml')

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

