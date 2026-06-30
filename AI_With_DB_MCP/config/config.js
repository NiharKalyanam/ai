/**
 * MASTER CONFIG — swap DB, AI model, or add tools here.
 * No other file needs to change.
 */

export const config = {
  // ─── SERVER ──────────────────────────────────────────────────────────────
  server: {
    name: process.env.MCP_SERVER_NAME || 'mcp-db-server',
    version: '1.0.0',
  },

  // ─── DATABASE ─────────────────────────────────────────────────────────────
  // Set DB_TYPE to: mysql | postgres | sqlite
  database: {
    type: process.env.DB_TYPE || 'mysql',       // swap here — nothing else changes
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '3306'),
    name: process.env.DB_NAME || 'identityiq',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    file: process.env.DB_FILE || './data.db',   // sqlite only
    tablePrefix: process.env.DB_TABLE_PREFIX || '', // e.g. 'spt_' to filter tables
    connectionLimit: 10,
  },

  // ─── AI MODEL ─────────────────────────────────────────────────────────────
  // Set AI_PROVIDER to: anthropic | openai | none
  ai: {
    provider: process.env.AI_PROVIDER || 'anthropic',
    model: process.env.AI_MODEL || 'claude-sonnet-4-5',
    apiKey: process.env.ANTHROPIC_API_KEY || process.env.OPENAI_API_KEY || '',
    maxTokens: parseInt(process.env.AI_MAX_TOKENS || '2048'),
  },

  // ─── TOOLS ────────────────────────────────────────────────────────────────
  // Drop a new file in src/tools/ and register it here. That's it.
  tools: {
    enabled: (process.env.MCP_TOOLS || 'query_database,describe_schema,sample_data,search_records').split(',').map(t => t.trim()),
  },

  // ─── SCHEMA DISCOVERY ─────────────────────────────────────────────────────
  schema: {
    autoDiscover: process.env.SCHEMA_AUTO_DISCOVER !== 'false',  // default true
    maxTablesInContext: parseInt(process.env.SCHEMA_MAX_TABLES || '50'),
    enumColumnNames: (process.env.SCHEMA_ENUM_COLUMNS || 'status,state,type,phase,action,op,operation,source,level,completion_status,result,severity,outcome').split(','),
    maxEnumValues: parseInt(process.env.SCHEMA_MAX_ENUM_VALUES || '15'),
    skipColumns: (process.env.SCHEMA_SKIP_COLUMNS || 'attributes,xml,extended_attributes,scorecard,preferences,arguments,config').split(','),
  },

  // ─── SAFETY ───────────────────────────────────────────────────────────────
  safety: {
    allowedStatements: ['SELECT', 'WITH'],
    blockedKeywords: ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE'],
    maxRowsReturned: parseInt(process.env.MAX_ROWS || '500'),
  },
};
