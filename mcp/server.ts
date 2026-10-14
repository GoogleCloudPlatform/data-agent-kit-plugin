/*
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import {Server} from '@modelcontextprotocol/sdk/server/index.js';
import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import psList from 'ps-list';


import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import {z} from 'zod';
import {deleteCell} from './tools/delete_cell.js';
import {insertCell} from './tools/insert_cell.js';
import {listCells} from './tools/list_cells.js';
import {readCell} from './tools/read_cell.js';
import {replaceCell} from './tools/replace_cell.js';
import {getNotebookInfo} from './tools/get_notebook_info.js';
import {searchCells} from './tools/search_cells.js';
import {createNotebook} from './tools/create_notebook.js';
import {getCellOutputs} from './tools/get_cell_outputs.js';

const args = process.argv;
const mode = args.find(a => a.startsWith('--mode='))?.split('=')[1];



const server = new Server(
  {
    name:
      mode === 'visualization'
        ? 'visualization'
        : mode === 'data-agent-kit'
          ? 'data-agent-kit'
          : 'notebook',
    version: '0.1.0',
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

let notebookClient: any = null;
let vizClient: any = null;
let dakClient: any = null;

const LOCAL_TOOLS = [
  {
    name: 'list_cells',
    description: 'List all cells in a notebook',
    inputSchema: {
      type: 'object',
      properties: {
        notebookPath: {
          type: 'string',
          description: 'Path to the notebook file',
        },
        maxLength: {
          type: 'number',
          description: 'Maximum length of the preview snippet for each cell (optional, defaults to 100)',
        },
      },
      required: ['notebookPath'],
    },
  },
  {
    name: 'read_cell',
    description: 'Read the content of a specific cell in a notebook',
    inputSchema: {
      type: 'object',
      properties: {
        notebookPath: {
          type: 'string',
          description: 'Path to the notebook file',
        },
        cellIndex: {
          type: 'number',
          description: '0-based index of the cell',
        },
      },
      required: ['notebookPath', 'cellIndex'],
    },
  },
  {
    name: 'insert_cell',
    description: 'Insert a new cell into a notebook',
    inputSchema: {
      type: 'object',
      properties: {
        notebookPath: {
          type: 'string',
          description: 'Path to the notebook file',
        },
        cellIndex: {
          type: 'number',
          description:
            'Index at which to insert the cell (omitted to append)',
        },
        cellType: {
          type: 'string',
          enum: ['code', 'markdown'],
          description: 'Type of cell',
        },
        content: {type: 'string', description: 'Content of the cell'},
      },
      required: ['notebookPath', 'cellType', 'content'],
    },
  },
  {
    name: 'replace_cell',
    description: 'Replace the content of a specific cell in a notebook',
    inputSchema: {
      type: 'object',
      properties: {
        notebookPath: {
          type: 'string',
          description: 'Path to the notebook file',
        },
        cellIndex: {
          type: 'number',
          description: '0-based index of the cell to replace',
        },
        content: {type: 'string', description: 'New content of the cell'},
      },
      required: ['notebookPath', 'cellIndex', 'content'],
    },
  },
  {
    name: 'delete_cell',
    description: 'Delete a specific cell from a notebook',
    inputSchema: {
      type: 'object',
      properties: {
        notebookPath: {
          type: 'string',
          description: 'Path to the notebook file',
        },
        cellIndex: {
          type: 'number',
          description: '0-based index of the cell to delete',
        },
      },
      required: ['notebookPath', 'cellIndex'],
    },
  },
  {
    name: 'get_notebook_info',
    description: 'Get summary information about a notebook',
    inputSchema: {
      type: 'object',
      properties: {
        notebookPath: {
          type: 'string',
          description: 'Path to the notebook file',
        },
      },
      required: ['notebookPath'],
    },
  },
  {
    name: 'search_cells',
    description: 'Search for text within cells of a notebook',
    inputSchema: {
      type: 'object',
      properties: {
        notebookPath: {
          type: 'string',
          description: 'Path to the notebook file',
        },
        query: {
          type: 'string',
          description: 'Text to search for',
        },
        caseSensitive: {
          type: 'boolean',
          description: 'Whether search is case sensitive (optional)',
        },
      },
      required: ['notebookPath', 'query'],
    },
  },
  {
    name: 'create_notebook',
    description: 'Create a new notebook file in the workspace',
    inputSchema: {
      type: 'object',
      properties: {
        directory: {
          type: 'string',
          description: 'Absolute path to the directory where the notebook should be created',
        },
        filename: {
          type: 'string',
          description: 'Name of the notebook file (without extension)',
        },
      },
      required: ['directory', 'filename'],
    },
  },
  {
    name: 'get_cell_outputs',
    description: 'Read outputs from a code cell by index',
    inputSchema: {
      type: 'object',
      properties: {
        notebookPath: {
          type: 'string',
          description: 'Path to the notebook file',
        },
        cellIndex: {
          type: 'number',
          description: '0-based index of the cell to inspect',
        },
      },
      required: ['notebookPath', 'cellIndex'],
    },
  },
];

const toolOwnerMap = new Map<string, 'notebook' | 'viz' | 'dak'>();

server.setRequestHandler(ListToolsRequestSchema, async () => {
  let aggregatedTools: any[] = [];
  toolOwnerMap.clear();

  if (mode === 'notebook') {
    if (notebookClient) {
      try {
        const response = await notebookClient.listTools();
        response.tools.forEach((t: any) => toolOwnerMap.set(t.name, 'notebook'));
        aggregatedTools.push(...response.tools);
      } catch (e) {
        console.error('Error listing tools from notebook client:', e);
      }
    } else {
      LOCAL_TOOLS.forEach((t: any) => toolOwnerMap.set(t.name, 'notebook'));
      aggregatedTools.push(...LOCAL_TOOLS);
    }
  }

  if (mode === 'visualization') {
    if (vizClient) {
      try {
        const response = await vizClient.listTools();
        response.tools.forEach((t: any) => toolOwnerMap.set(t.name, 'viz'));
        aggregatedTools.push(...response.tools);
      } catch (e) {
        console.error('Error listing tools from viz client:', e);
      }
    }
  }

  if (mode === 'data-agent-kit') {
    if (dakClient) {
      try {
        const response = await dakClient.listTools();
        response.tools.forEach((t: any) => toolOwnerMap.set(t.name, 'dak'));
        aggregatedTools.push(...response.tools);
      } catch (e) {
        console.error('Error listing tools from dak client:', e);
      }
    }
  }

  return { tools: aggregatedTools };
});

// Zod schemas for validation
const NotebookPathSchema = z.object({
  notebookPath: z.string(),
});

const ListCellsSchema = NotebookPathSchema.extend({
  maxLength: z.number().optional(),
});

const CellIndexSchema = NotebookPathSchema.extend({
  cellIndex: z.number(),
});

const InsertCellSchema = NotebookPathSchema.extend({
  cellIndex: z.number().optional(),
  cellType: z.enum(['code', 'markdown']),
  content: z.string(),
});

const ReplaceCellSchema = CellIndexSchema.extend({
  content: z.string(),
});

const SearchCellsSchema = NotebookPathSchema.extend({
  query: z.string(),
  caseSensitive: z.boolean().optional(),
});

const CreateNotebookSchema = z.object({
  directory: z.string(),
  filename: z.string(),
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const {name, arguments: args} = request.params;

  const owner = toolOwnerMap.get(name);

  if (owner === 'notebook' && notebookClient) {
    return await notebookClient.callTool({ name, arguments: args });
  }

  if (owner === 'viz' && vizClient) {
    return await vizClient.callTool({ name, arguments: args });
  }

  if (owner === 'dak' && dakClient) {
    return await dakClient.callTool({ name, arguments: args });
  }

  if ((mode === 'visualization' || mode === 'data-agent-kit') && !owner) {
     throw new Error(`Tool ${name} not available in ${mode} mode`);
  }

  try {
    switch (name) {
      case 'list_cells': {
        const parsed = ListCellsSchema.parse(args);
        const result = await listCells(parsed.notebookPath, parsed.maxLength);
        return {
          content: [{type: 'text', text: JSON.stringify(result, null, 2)}],
        };
      }
      case 'read_cell': {
        const parsed = CellIndexSchema.parse(args);
        const result = await readCell(parsed.notebookPath, parsed.cellIndex);
        return {
          content: [{type: 'text', text: JSON.stringify(result, null, 2)}],
        };
      }
      case 'insert_cell': {
        const parsed = InsertCellSchema.parse(args);
        const result = await insertCell(
          parsed.notebookPath,
          parsed.cellType,
          parsed.content,
          parsed.cellIndex,
        );
        return {
          content: [{type: 'text', text: JSON.stringify(result, null, 2)}],
        };
      }
      case 'replace_cell': {
        const parsed = ReplaceCellSchema.parse(args);
        const result = await replaceCell(
          parsed.notebookPath,
          parsed.cellIndex,
          parsed.content,
        );
        return {
          content: [{type: 'text', text: JSON.stringify(result, null, 2)}],
        };
      }
      case 'delete_cell': {
        const parsed = CellIndexSchema.parse(args);
        const result = await deleteCell(parsed.notebookPath, parsed.cellIndex);
        return {
          content: [{type: 'text', text: JSON.stringify(result, null, 2)}],
        };
      }
      case 'get_notebook_info': {
        const parsed = NotebookPathSchema.parse(args);
        const result = await getNotebookInfo(parsed.notebookPath);
        return {
          content: [{type: 'text', text: JSON.stringify(result, null, 2)}],
        };
      }
      case 'search_cells': {
        const parsed = SearchCellsSchema.parse(args);
        const result = await searchCells(parsed.notebookPath, parsed.query, parsed.caseSensitive);
        return {
          content: [{type: 'text', text: JSON.stringify(result, null, 2)}],
        };
      }
      case 'create_notebook': {
        const parsed = CreateNotebookSchema.parse(args);
        const result = await createNotebook(parsed.directory, parsed.filename);
        return {
          content: [{type: 'text', text: JSON.stringify(result, null, 2)}],
        };
      }
      case 'get_cell_outputs': {
        const parsed = CellIndexSchema.parse(args);
        const result = await getCellOutputs(parsed.notebookPath, parsed.cellIndex);
        return {
          content: result,
        };
      }
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(`Invalid arguments for ${name}: ${error.message}`);
    }
    throw error;
  }
});

const IDE_MAPPING: Record<string, string> = {
  'code': 'visualstudiocode',
  'code-insiders': 'visualstudiocode',
  'cursor': 'cursor',
  'antigravity': 'antigravity'
};

async function inferIdeName(): Promise<string | null> {
  try {
    const processes = await psList();
    let currentPid = process.pid;
    let depth = 0;
    const maxDepth = 20;
    
    while (currentPid && currentPid > 1 && depth < maxDepth) {
      const proc = processes.find(p => p.pid === currentPid);
      if (!proc) break;
      
      const name = proc.name.toLowerCase();
      for (const key in IDE_MAPPING) {
        if (name.includes(key)) {
          return IDE_MAPPING[key];
        }
      }
      
      currentPid = proc.ppid;
      depth++;
    }
  } catch (error) {
    console.error('Error parsing process tree:', error);
  }
  return null;
}

async function startStandaloneServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Standalone Notebook MCP server running on stdio');
}

async function run() {
  let ideName = process.env.DATA_CLOUD_CURR_IDE_NAME;
  if (!ideName) {
    ideName = await inferIdeName();
    if (ideName) {
      console.error(`Inferred IDE name from process tree: ${ideName}`);
    }
  }

  if (ideName) {

    const proxyCmd = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../bin/mcp_proxy_bundle.cjs');
    
    // Connect to Notebooks proxy
    if (mode === 'notebook') {
      try {
        const notebookTransport = new StdioClientTransport({
          command: process.execPath,
          args: [proxyCmd, `notebooks-${ideName.toLowerCase()}`],
          env: process.env
        });
        notebookClient = new Client({ name: 'notebook-client', version: '0.1.0' }, { capabilities: {} });
        await notebookClient.connect(notebookTransport);
      } catch (e) {
        notebookClient = null;
      }
    }

    // Connect to Visualization proxy
    if (mode === 'visualization') {
      try {
        const vizTransport = new StdioClientTransport({
          command: process.execPath,
          args: [proxyCmd, `visualization-${ideName.toLowerCase()}`],
          env: process.env
        });
        vizClient = new Client({ name: 'viz-client', version: '0.1.0' }, { capabilities: {} });
        await vizClient.connect(vizTransport);
      } catch (e) {
        vizClient = null;
      }
    }

    // Connect to Data Agent Kit proxy
    if (mode === 'data-agent-kit') {
      try {
        const dakTransport = new StdioClientTransport({
          command: process.execPath,
          args: [proxyCmd, `dataAgentKit-${ideName.toLowerCase()}`],
          env: process.env
        });
        dakClient = new Client({ name: 'dak-client', version: '0.1.0' }, { capabilities: {} });
        await dakClient.connect(dakTransport);
      } catch (e) {
        dakClient = null;
      }
    }

    // Fallback strategy Scenario 4: All fail -> Standalone
    if (!notebookClient && !vizClient && !dakClient) {
      await startStandaloneServer();
      return;
    }

    // Start the master server on stdio
    const transport = new StdioServerTransport();
    await server.connect(transport);
    return;
  }

  await startStandaloneServer();
}

run().catch((error) => {
  console.error('Fatal error running server:', error);
  process.exit(1);
});
