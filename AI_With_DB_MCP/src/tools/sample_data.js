/**
 * Tool: sample_data
 * Returns sample rows from any table. Great for exploring an unknown DB.
 */

export const name = 'sample_data';

export const definition = {
  name,
  description: 'Show sample rows from a database table. Use this to understand what data looks like before querying.',
  inputSchema: {
    type: 'object',
    properties: {
      table: {
        type: 'string',
        description: 'Table name to sample from.',
      },
      limit: {
        type: 'number',
        description: 'Number of rows to return (default: 5, max: 20).',
        default: 5,
      },
      columns: {
        type: 'array',
        items: { type: 'string' },
        description: 'Optional: specific columns to include. Omit for all columns.',
      },
    },
    required: ['table'],
  },
};

export function createHandler({ adapter, schema, safety, safetyConfig }) {
  return async function ({ table, limit = 5, columns }) {
    const cap = Math.min(limit, 20);

    // Validate table exists
    if (!schema.hasTable(table)) {
      const tables = Object.keys(schema.getSchema()).slice(0, 10).join(', ');
      return { content: [{ type: 'text', text: `Table "${table}" not in schema.\nSome available tables: ${tables}` }], isError: true };
    }

    // Build safe SELECT
    const colList = columns?.length
      ? columns.map(c => `\`${c}\``).join(', ')
      : '*';

    // Build a db-type-aware LIMIT query
    const sql = `SELECT ${colList} FROM \`${table}\` LIMIT ${cap}`;

    let result;
    try {
      result = await adapter.query(sql);
    } catch (e) {
      // Try without backticks (postgres)
      try {
        const sql2 = `SELECT ${columns?.length ? columns.join(', ') : '*'} FROM "${table}" LIMIT ${cap}`;
        result = await adapter.query(sql2);
      } catch (e2) {
        return { content: [{ type: 'text', text: `Failed to sample table: ${e2.message}` }], isError: true };
      }
    }

    const lines = [`**Sample from \`${table}\`** (${result.rowCount} rows)\n`];
    if (result.rowCount === 0) {
      lines.push('Table is empty.');
    } else {
      // Markdown table
      const fields = result.fields;
      lines.push('| ' + fields.join(' | ') + ' |');
      lines.push('| ' + fields.map(() => '---').join(' | ') + ' |');
      for (const row of result.rows) {
        lines.push('| ' + fields.map(f => {
          const v = row[f];
          if (v === null || v === undefined) return 'NULL';
          const s = String(v);
          return s.length > 60 ? s.slice(0, 57) + '...' : s;
        }).join(' | ') + ' |');
      }
    }

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  };
}
