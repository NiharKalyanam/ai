/**
 * Tool Registry
 * Dynamically loads tool files from src/tools/.
 * To add a new tool: drop a file in src/tools/ + add its name to MCP_TOOLS in .env.
 * No other code changes needed.
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readdir } from 'fs/promises';

const __dir = dirname(fileURLToPath(import.meta.url));

export class ToolRegistry {
  constructor() {
    this.tools = new Map(); // name → { definition, handler }
  }

  /**
   * Load tools by name from src/tools/ directory.
   * Each tool file exports: { name, definition, createHandler(context) }
   */
  async load(enabledNames, context) {
    const toolsDir = join(__dir, '../tools');

    // Discover all available tool files
    let files;
    try {
      files = await readdir(toolsDir);
    } catch {
      console.error('[Tools] No tools directory found.');
      return;
    }

    const available = {};
    for (const file of files.filter(f => f.endsWith('.js'))) {
      try {
        const mod = await import(join(toolsDir, file));
        if (mod.name) available[mod.name] = mod;
      } catch (e) {
        console.error(`[Tools] Failed to load ${file}: ${e.message}`);
      }
    }

    // Register only the enabled ones
    for (const name of enabledNames) {
      const mod = available[name];
      if (!mod) {
        console.error(`[Tools] Tool "${name}" not found. Available: ${Object.keys(available).join(', ')}`);
        continue;
      }
      const handler = mod.createHandler(context);
      this.tools.set(name, { definition: mod.definition, handler });
      console.error(`[Tools] Registered: ${name}`);
    }
  }

  /** Get all MCP tool definitions (for server.setRequestHandler ListTools) */
  getDefinitions() {
    return Array.from(this.tools.values()).map(t => t.definition);
  }

  /** Execute a tool by name */
  async execute(name, args) {
    const tool = this.tools.get(name);
    if (!tool) throw new Error(`Unknown tool: ${name}. Available: ${[...this.tools.keys()].join(', ')}`);
    return await tool.handler(args);
  }

  has(name) { return this.tools.has(name); }
  list() { return [...this.tools.keys()]; }
}
