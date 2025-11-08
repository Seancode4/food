# Basic MCP Server

A minimal Model Context Protocol (MCP) server with one tool, written in Python.

## Setup

1. Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies (for testing):
```bash
npm install
```

## Usage

Run the server directly (make sure venv is activated):
```bash
python3 server.py
```

Or using npm:
```bash
npm start
```

## Testing with npx

Test the server using the MCP Inspector:

```bash
npm test
```

Or directly with npx:
```bash
npx @modelcontextprotocol/inspector python3 server.py
```

This will:
1. Start the MCP Inspector (opens in browser at `http://localhost:6274/`)
2. Launch your Python server
3. Allow you to interactively test the server's tools

In the Inspector interface, you can:
- View available tools
- Test the `echo` tool with custom inputs
- Monitor server logs and notifications

## Tool Details

- **Name**: `echo`
- **Description**: Echo back the input message
- **Input**: `{ message: string }`
- **Output**: Echoed message

## Frontend Chatbot with LLM

A web-based chatbot interface powered by OpenAI that can intelligently use MCP tools.

### Setup

1. Install Node.js dependencies (if not already installed):
```bash
npm install
```

2. Set up OpenAI API key:
```bash
export OPENAI_API_KEY=your-api-key-here
```

Or create a `.env` file (not included in git):
```
OPENAI_API_KEY=your-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

3. Start the backend server:
```bash
npm run backend
```

Or:
```bash
npm run chatbot
```

4. Open `chatbot.html` in your web browser

### Usage

- The backend server runs on `http://localhost:3000`
- Open `chatbot.html` in your browser
- Chat naturally with the LLM - it will automatically use MCP tools when needed
- Example: "Can you echo 'hello world'?" or "Use the echo tool to say hi"

### How It Works

1. **LLM Integration**: Uses OpenAI GPT-4o-mini for natural language understanding
2. **Tool Discovery**: Automatically discovers available MCP tools
3. **Function Calling**: LLM decides when to call tools based on user requests
4. **Tool Execution**: Tools are executed via MCP server
5. **Response Generation**: LLM generates natural responses using tool results

### Files

- `backend.js` - Node.js backend server that bridges the frontend, LLM, and MCP server
- `chatbot.html` - Frontend chatbot interface with a plain UI