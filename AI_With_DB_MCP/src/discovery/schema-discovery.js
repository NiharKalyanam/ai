/**
 * Schema Discovery Engine
 * Auto-reads any connected DB and builds a rich context string.
 * No table names, column names, or values are hardcoded here.
 */

export class SchemaDiscovery {
  constructor(adapter, schemaConfig) {
    this.adapter = adapter;
    this.cfg = schemaConfig;
    this.schema = null;       // raw schema data
    this.schemaText = '';     // LLM-ready text
    this.lastBuilt = null;
  }

  /** Build schema from the live database */
  async build() {
    console.error('[Schema] Auto-discovering schema...');
    const prefix = this.adapter.config?.tablePrefix || '';
    const tables = await this.adapter.getTables(prefix);
    const maxTables = this.cfg.maxTablesInContext;
    const enumCols = new Set(this.cfg.enumColumnNames.map(c => c.toLowerCase()));

    const schema = {};
    const lines = [
      `DATABASE SCHEMA (auto-discovered from live ${this.adapter.type} database):`,
      `DB Name: ${this.adapter.config.name || this.adapter.config.file}`,
      `Total tables: ${tables.length}`,
      '',
    ];

    for (const tableName of tables.slice(0, maxTables)) {
      let columns;
      try {
        columns = await this.adapter.getColumns(tableName);
      } catch (e) {
        console.error(`[Schema] Could not read columns for ${tableName}: ${e.message}`);
        continue;
      }

      schema[tableName] = { columns: [] };
      lines.push(`TABLE ${tableName}:`);

      for (const col of columns) {
        const colInfo = { name: col.name, type: col.type, values: null };
        let colLine = `  - ${col.name} (${col.type})`;

        // Auto-detect enum-like columns and fetch real values
        const colLower = col.name.toLowerCase();
        const isTextType = ['varchar', 'char', 'text', 'character varying', 'string'].includes(col.type.toLowerCase());
        const isEnumCandidate = enumCols.has(colLower) && isTextType;

        if (isEnumCandidate) {
          try {
            const vals = await this.adapter.getDistinctValues(tableName, col.name, this.cfg.maxEnumValues);
            if (vals.length > 0 && vals.length <= this.cfg.maxEnumValues) {
              colInfo.values = vals;
              colLine += ` -- real values: ${vals.map(v => `'${v}'`).join(', ')}`;
            }
          } catch (e) { /* skip — table might be empty */ }
        }

        schema[tableName].columns.push(colInfo);
        lines.push(colLine);
      }

      lines.push('');
    }

    if (tables.length > maxTables) {
      lines.push(`... and ${tables.length - maxTables} more tables (increase SCHEMA_MAX_TABLES to include them)`);
    }

    this.schema = schema;
    this.schemaText = lines.join('\n');
    this.lastBuilt = new Date();
    console.error(`[Schema] Done. ${Object.keys(schema).length} tables processed.`);
    return this;
  }

  /** Get schema as structured object */
  getSchema() { return this.schema; }

  /** Get schema as LLM-ready text */
  getText() { return this.schemaText; }

  /** Get column names for a specific table */
  getColumns(tableName) {
    return this.schema?.[tableName]?.columns?.map(c => c.name) || [];
  }

  /** Check if a table exists in schema */
  hasTable(tableName) {
    return !!this.schema?.[tableName];
  }

  /** Summary for display */
  getSummary() {
    const tableCount = Object.keys(this.schema || {}).length;
    const colCount = Object.values(this.schema || {}).reduce((s, t) => s + t.columns.length, 0);
    return `${tableCount} tables, ${colCount} columns (built at ${this.lastBuilt?.toISOString()})`;
  }
}
