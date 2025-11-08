#!/usr/bin/env node

import express from 'express';
import cors from 'cors';
import OpenAI from 'openai';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

let mcpClient = null;
let mcpTransport = null;

// OpenAI API Key - can be set via environment variable or use hardcoded fallback
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "None";

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: OPENAI_API_KEY,
});

// Initialize MCP client connection
async function initMCPClient() {
  try {
    const pythonPath = join(__dirname, 'venv', 'bin', 'python');
    const serverPath = join(__dirname, 'server.py');
    
    mcpTransport = new StdioClientTransport({
      command: pythonPath,
      args: [serverPath],
      env: process.env,
    });

    mcpClient = new Client(
      {
        name: 'chatbot-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      }
    );

    await mcpClient.connect(mcpTransport);
    console.log('Connected to MCP server');
  } catch (error) {
    console.error('Failed to connect to MCP server:', error);
    throw error;
  }
}

// List available tools
app.get('/api/tools', async (req, res) => {
  try {
    if (!mcpClient) {
      await initMCPClient();
    }
    
    const tools = await mcpClient.listTools();
    res.json(tools);
  } catch (error) {
    console.error('Error listing tools:', error);
    res.status(500).json({ error: error.message });
  }
});

// Call a tool
app.post('/api/tools/call', async (req, res) => {
  try {
    const { name, arguments: args } = req.body;
    
    if (!mcpClient) {
      await initMCPClient();
    }
    
    const result = await mcpClient.callTool({
      name,
      arguments: args || {},
    });
    
    res.json(result);
  } catch (error) {
    console.error('Error calling tool:', error);
    res.status(500).json({ error: error.message });
  }
});

// Convert MCP tools to OpenAI function definitions
function convertMCPToolsToOpenAI(mcpTools) {
  return mcpTools.tools.map(tool => ({
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description || '',
      parameters: tool.inputSchema || {},
    },
  }));
}

// Chat endpoint with LLM
app.post('/api/chat', async (req, res) => {
  try {
    const { message, history = [] } = req.body;

    if (!mcpClient) {
      await initMCPClient();
    }

    // Get available tools from MCP server
    const mcpTools = await mcpClient.listTools();
    const functions = convertMCPToolsToOpenAI(mcpTools);

    // Build conversation history
    const messages = [
      {
        role: 'system',
        content: 'You are a helpful assistant that can use tools to help users. When you need to use a tool, call it with the appropriate parameters.',
      },
      ...history,
      {
        role: 'user',
        content: message,
      },
    ];

    // Call OpenAI with function calling
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: messages,
      tools: functions.length > 0 ? functions : undefined,
      tool_choice: functions.length > 0 ? 'auto' : undefined,
    });

    const assistantMessage = completion.choices[0].message;
    let response = {
      content: assistantMessage.content || '',
      toolCalls: [],
    };

    // Handle tool calls
    if (assistantMessage.tool_calls && assistantMessage.tool_calls.length > 0) {
      const toolResults = [];

      for (const toolCall of assistantMessage.tool_calls) {
        const toolName = toolCall.function.name;
        const toolArgs = JSON.parse(toolCall.function.arguments || '{}');

        // Execute tool via MCP
        const toolResult = await mcpClient.callTool({
          name: toolName,
          arguments: toolArgs,
        });

        // Extract result text
        let resultText = '';
        if (toolResult.content && toolResult.content.length > 0) {
          resultText = toolResult.content[0].text || JSON.stringify(toolResult.content[0]);
        } else {
          resultText = JSON.stringify(toolResult);
        }

        toolResults.push({
          tool_call_id: toolCall.id,
          role: 'tool',
          name: toolName,
          content: resultText,
        });

        response.toolCalls.push({
          name: toolName,
          arguments: toolArgs,
          result: resultText,
        });
      }

      // Send tool results back to LLM for final response
      const followUpMessages = [
        ...messages,
        assistantMessage,
        ...toolResults,
      ];

      const followUpCompletion = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: followUpMessages,
      });

      response.content = followUpCompletion.choices[0].message.content || response.content;
    }

    res.json(response);
  } catch (error) {
    console.error('Error in chat:', error);
    res.status(500).json({ error: error.message });
  }
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    connected: mcpClient !== null,
    openaiConfigured: !!OPENAI_API_KEY && OPENAI_API_KEY !== '',
  });
});

app.listen(PORT, async () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
  await initMCPClient();
});

