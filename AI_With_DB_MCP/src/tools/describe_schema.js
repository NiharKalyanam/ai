/**
 * Tool: describe_schema
 * Returns the full auto-discovered schema for the connected database.
 */

export const name = 'describe_schema';

export const definition = {
  name,
  description: 'Show the database schema: all tables, columns, types, and known enum values. Use this before writing queries.',
  inputSchema: {
    type: 'object',
    properties: {
      table: {
        type: 'string',
        description: 'Optional: filter to a specific table name.',
      },
      summary: {
        type: 'boolean',
        description: 'If true, return only a summary (table names + column count).',
        default: false,
      },
    },
  },
};

export function createHandler({ adapter, schema }) {
  return async function ({ table, summary = false } = {}) {
    const raw = schema.getSchema();

    if (!raw || Object.keys(raw).length === 0) {
      return { content: [{ type: 'text', text: 'Schema not yet built. Try again in a moment.' }] };
    }

    // Filter to one table if requested
    if (table) {
      const tableData = raw[table];
      if (!tableData) {
        const available = Object.keys(raw).join(', ');
        return { content: [{ type: 'text', text: `Table "${table}" not found.\nAvailable: ${available}` }] };
      }
      const lines = [`**Table: ${table}**\n`];
      for (const col of tableData.columns) {
        let line = `- \`${col.name}\` (${col.type})`;
        if (col.values?.length) line += `  → values: ${col.values.map(v => `'${v}'`).join(', ')}`;
        lines.push(line);
      }
      return { content: [{ type: 'text', text: lines.join('\n') }] };
    }

    if (summary) {
      const lines = [`**Schema Summary** — ${adapter.type} / ${adapter.config.name || adapter.config.file}\n`];
      for (const [tname, tdata] of Object.entries(raw)) {
        lines.push(`- \`${tname}\` (${tdata.columns.length} columns)`);
      }
      lines.push(`\nTotal: ${Object.keys(raw).length} tables`);
      return { content: [{ type: 'text', text: lines.join('\n') }] };
    }

    // Full schema text
    return { content: [{ type: 'text', text: schema.getText() }] };
  };
}
