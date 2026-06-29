#!/usr/bin/env node
/**
 * MCP DB Server — Entry Point
 * Wires: config → DB adapter → schema discovery → AI → tool registry → MCP server
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { config } from '../config/config.js';
import { createAdapter } from './adapters/adapter-factory.js';
import { createAI } from './adapters/ai-factory.js';
import { SchemaDiscovery } from './discovery/schema-discovery.js';
import { SafetyGuard } from './discovery/safety.js';
import { ToolRegistry } from './tools/registry.js';

async function main() {
  console.error(`\n🔌 MCP DB Server starting...`);
  console.error(`   DB:    ${config.database.type} / ${config.database.name || config.database.file}`);
  console.error(`   AI:    ${config.ai.provider} / ${config.ai.model}`);
  console.error(`   Tools: ${config.tools.enabled.join(', ')}\n`);

  // 1. Connect to database
  const adapter = await createAdapter(config.database);

  // 2. Discover schema
  const schema = new SchemaDiscovery(adapter, config.schema);
  if (config.schema.autoDiscover) {
    await schema.build();
    console.error(`[Schema] ${schema.getSummary()}`);
  }

  // 3. Initialize AI provider
  const ai = await createAI(config.ai);

  // 4. Safety guard
  const safety = new SafetyGuard(config.safety);

  // 5. Shared context passed to all tools
  const context = { adapter, schema, ai, safety, safetyConfig: config.safety };

  // 6. Load tools
  const registry = new ToolRegistry();
  await registry.load(config.tools.enabled, context);
  console.error(`[Tools] Active: ${registry.list().join(', ')}`);

  // 7. Create MCP server
  const server = new Server(
    { name: config.server.name, version: config.server.version },
    { capabilities: { tools: {} } }
  );

  // List tools
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: registry.getDefinitions(),
  }));

  // Execute tool
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    console.error(`[Tool] Calling: ${name}`, JSON.stringify(args));
    try {
      return await registry.execute(name, args || {});
    } catch (e) {
      console.error(`[Tool] Error in ${name}:`, e.message);
      return {
        content: [{ type: 'text', text: `Tool error: ${e.message}` }],
        isError: true,
      };
    }
  });

  // 8. Connect transport
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`\n✅ MCP server ready. Listening on stdio.\n`);
}

main().catch(e => {
  console.error('Fatal error:', e);
  process.exit(1);
});
