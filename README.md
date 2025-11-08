# Dartmouth Meal Planner

An AI-powered meal planning tool that helps you explore Dartmouth dining options, find food items, and get nutritional information to plan your meals.

## Quick Start

### 1. Install Dependencies

**Python dependencies:**
```bash
# Create virtual environment (if not already created)
python3.10 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install Python packages
pip install -r requirements.txt
```

**Node.js dependencies:**
```bash
npm install
```

### 2. Set Up OpenAI API Key

Edit `backend.js` and set your OpenAI API key on line 24:
```javascript
const OPENAI_API_KEY = 'your-api-key-here';
```

Or set it as an environment variable:
```bash
export OPENAI_API_KEY=your-api-key-here
```

### 3. Run the Application

**Start the backend server:**
```bash
npm run backend
```

**Open the chatbot:**
- Open `chatbot.html` in your web browser
- The backend runs on `http://localhost:3000`

## How to Use

### Ask What Types of Food Are Available

You can ask the chatbot about available food categories:

- **"What food categories are available?"**
- **"Show me all categories"**
- **"What types of entrees do you have?"**

The chatbot will show you all available food categories like:
- Entrees (Meat, Poultry, Seafood, etc.)
- Side Dishes (Potatoes, Rice, Vegetables, etc.)
- Desserts
- Beverages
- And more...

### Find Specific Food Items

Search for food items by name:

- **"Find me beef items"**
- **"What chicken options are available?"**
- **"Show me items in Entrees:Meat:Beef"**
- **"Get me the ID for Gluten Free Roll, Hamburger Bun"**

### Get Food Information and Nutrients

Get detailed information about any food item by its ID:

- **"Get recipe details for ID 1032"**
- **"Show me details for recipe ID 5765"**
- **"What are the ingredients for recipe ID 1032?"**
- **"Get nutritional information for recipe ID 5765"**

You can also request additional details:
- **"Get recipe details for ID 1032 with ingredients"** - Includes ingredient list
- **"Show me recipe 5765 with cooking methods"** - Includes cooking methods
- **"Get full details for ID 1032 including ingredients and methods"** - Includes everything

### Plan Your Meal

The chatbot can help you plan meals by:
- Exploring available options
- Finding items by category or name
- Getting detailed information including nutrients
- Comparing different food options

**Example conversation:**
```
You: "What beef entrees are available?"
Bot: [Shows list of beef entrees]

You: "Get details for recipe ID 5765"
Bot: [Shows recipe details, portion size, category, etc.]

You: "Show me the ingredients for that recipe"
Bot: [Shows ingredients if available]
```

## Features

- **Category Browsing**: Explore all available food categories
- **Item Search**: Find food items by name using smart matching
- **Detailed Information**: Get recipe details including:
  - Name and ID
  - Category
  - Portion size
  - Ingredients (optional)
  - Cooking methods (optional)
  - Nutritional information (optional)
- **AI-Powered**: Natural language interface - just ask questions!

## Troubleshooting

**Backend won't start:**
- Make sure Python 3.10+ is installed
- Activate the virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

**Chatbot can't connect:**
- Make sure the backend is running: `npm run backend`
- Check that it's running on `http://localhost:3000`
- Refresh the chatbot page in your browser

**API key issues:**
- Make sure your OpenAI API key is set in `backend.js` or as an environment variable
- Check the health endpoint: `http://localhost:3000/api/health`
