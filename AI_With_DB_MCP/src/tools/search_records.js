/**
 * Tool: search_records
 * Full-text-style keyword search across string columns of any table.
 * No AI required — pure SQL LIKE search, fully dynamic.
 */

export const name = 'search_records';

export const definition = {
  name,
  description: 'Search for records matching a keyword across string columns of any table.',
  inputSchema: {
    type: 'object',
    properties: {
      table: {
        type: 'string',
        description: 'Table to search in.',
      },
      keyword: {
        type: 'string',
        description: 'Keyword or phrase to search for.',
      },
      columns: {
        type: 'array',
        items: { type: 'string' },
        description: 'Columns to search in. If omitted, all varchar/text columns are searched.',
      },
      limit: {
        type: 'number',
        description: 'Max results (default: 20).',
        default: 20,
      },
    },
    required: ['table', 'keyword'],
  },
};

export function createHandler({ adapter, schema }) {
  return async function ({ table, keyword, columns, limit = 20 }) {
    const cap = Math.min(limit, 100);

    // Get string columns if not specified
    let searchCols = columns;
    if (!searchCols || searchCols.length === 0) {
      const allCols = schema.getSchema()?.[table]?.columns || [];
      searchCols = allCols
        .filter(c => ['varchar', 'char', 'text', 'character varying', 'string', 'longtext', 'mediumtext'].includes(c.type.toLowerCase()))
        .map(c => c.name)
        .slice(0, 10); // cap at 10 columns for performance
    }

    if (searchCols.length === 0) {
      return { content: [{ type: 'text', text: `No searchable string columns found in "${table}".` }] };
    }

    // Build WHERE clause dynamically
    const escaped = keyword.replace(/'/g, "''");
    const conditions = searchCols.map(c => `LOWER(${c}) LIKE LOWER('%${escaped}%')`).join(' OR ');
    const sql = `SELECT * FROM ${table} WHERE ${conditions} LIMIT ${cap}`;

    let result;
    try {
      result = await adapter.query(sql);
    } catch (e) {
      return { content: [{ type: 'text', text: `Search failed: ${e.message}\nSQL: ${sql}` }], isError: true };
    }

    const lines = [`**Search results for "${keyword}" in \`${table}\`** — ${result.rowCount} match(es)\n`];

    if (result.rowCount === 0) {
      lines.push('No matching records found.');
    } else {
      const fields = result.fields;
      lines.push('| ' + fields.join(' | ') + ' |');
      lines.push('| ' + fields.map(() => '---').join(' | ') + ' |');
      for (const row of result.rows) {
        lines.push('| ' + fields.map(f => {
          const v = row[f];
          if (v === null || v === undefined) return '';
          const s = String(v);
          return s.length > 80 ? s.slice(0, 77) + '...' : s;
        }).join(' | ') + ' |');
      }
    }

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  };
}
