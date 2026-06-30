# MCP DB Server — Pluggable Database MCP Server

A **production-grade MCP server** that connects any AI client (Claude Desktop, Cursor, Windsurf) to any database. Fully pluggable — swap DB, AI model, or tools by editing `.env` only.

---

## Architecture

```
Claude Desktop / Cursor / Any MCP Client
         │  stdio (JSON-RPC)
         ▼
    src/index.js  ← wires everything
         │
         ├── config/config.js         ← single source of truth
         │
         ├── src/adapters/
         │   ├── adapter-factory.js   ← picks MySQL / Postgres / SQLite
         │   ├── mysql.js
         │   ├── postgres.js
         │   ├── sqlite.js
         │   └── ai-factory.js        ← picks Anthropic / OpenAI / none
         │
         ├── src/discovery/
         │   ├── schema-discovery.js  ← auto-reads ANY database schema
         │   └── safety.js            ← blocks dangerous queries
         │
         └── src/tools/
             ├── registry.js          ← dynamic tool loader
             ├── query_database.js    ← NL → SQL → results
             ├── describe_schema.js   ← show DB structure
             ├── sample_data.js       ← preview any table
             └── search_records.js    ← keyword search
```

---

## Quick Start

```bash
# 1. Install
npm install

# 2. Configure
cp .env.example .env
# Edit .env with your DB credentials and API key

# 3. Run (test it)
node src/index.js
```

---

## Swap the Database

Edit `.env` — no code changes needed:

```env
# MySQL (default)
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mydb
DB_USER=root
DB_PASSWORD=secret

# Postgres
DB_TYPE=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_USER=postgres
DB_PASSWORD=secret

# SQLite
DB_TYPE=sqlite
DB_FILE=./my-database.db
```

---

## Swap the AI Model

```env
# Use Anthropic Claude (default)
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-...

# Use OpenAI GPT
AI_PROVIDER=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# No AI (tools like describe_schema and sample_data still work)
AI_PROVIDER=none
```

---

## Add a New Tool

1. Create `src/tools/my_tool.js`:

```js
export const name = 'my_tool';

export const definition = {
  name,
  description: 'What this tool does.',
  inputSchema: {
    type: 'object',
    properties: {
      input: { type: 'string', description: 'Some input' },
    },
    required: ['input'],
  },
};

export function createHandler({ adapter, schema, safety }) {
  return async function ({ input }) {
    // Your logic here
    const result = await adapter.query(`SELECT * FROM my_table WHERE name = '${input}' LIMIT 10`);
    return { content: [{ type: 'text', text: JSON.stringify(result.rows) }] };
  };
}
```

2. Add its name to `.env`:

```env
MCP_TOOLS=query_database,describe_schema,sample_data,search_records,my_tool
```

That's it. No other files to touch.

---

## Add a New Database Adapter

1. Create `src/adapters/mymongo.js` extending `BaseAdapter`
2. Register it in `adapter-factory.js`:

```js
import { MyMongoAdapter } from './mymongo.js';
const REGISTRY = {
  mysql: MySQLAdapter,
  postgres: PostgresAdapter,
  sqlite: SQLiteAdapter,
  mongodb: MyMongoAdapter,  // ← add here
};
```

3. Set `DB_TYPE=mongodb` in `.env`

---

## Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "mcp-db-server": {
      "command": "node",
      "args": ["/absolute/path/to/mcp-db-server/src/index.js"],
      "env": {
        "DB_TYPE": "mysql",
        "DB_HOST": "localhost",
        "DB_NAME": "identityiq",
        "DB_USER": "root",
        "DB_PASSWORD": "your-password",
        "ANTHROPIC_API_KEY": "sk-ant-your-key",
        "MCP_TOOLS": "query_database,describe_schema,sample_data,search_records"
      }
    }
  }
}
```

Windows path: `%APPDATA%\Claude\claude_desktop_config.json`

---

## Connect to Cursor / Windsurf

In Cursor Settings → MCP → Add Server:

```json
{
  "mcpServers": {
    "mcp-db-server": {
      "command": "node",
      "args": ["/path/to/mcp-db-server/src/index.js"]
    }
  }
}
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `query_database` | Ask in plain English → get SQL + results + table |
| `describe_schema` | Show all tables, columns, and enum values |
| `sample_data` | Preview rows from any table |
| `search_records` | Keyword search across string columns |

---

## Filter Tables by Prefix

Your IIQ database has `spt_` tables. Only expose those:

```env
DB_TABLE_PREFIX=spt_
```

For a fresh database with no prefix, leave it blank.

---

## Security

- All queries validated before execution — only SELECT/WITH allowed
- Configurable blocked keywords (INSERT, UPDATE, DELETE, DROP, etc.)
- Auto LIMIT applied if missing
- Use a read-only DB user in production
