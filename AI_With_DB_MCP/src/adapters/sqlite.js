import { BaseAdapter } from './base.js';

export class SQLiteAdapter extends BaseAdapter {
  constructor(config) {
    super(config);
    this.db = null;
  }

  async connect() {
    let Database;
    try {
      const mod = await import('better-sqlite3');
      Database = mod.default;
    } catch (e) {
      throw new Error(
        'SQLite requires better-sqlite3: npm install better-sqlite3\n' +
        'Note: better-sqlite3 requires Node.js v20 or v22.\n' +
        'If you are on Node v24, switch with: nvm use 22\n' +
        `Original error: ${e.message}`
      );
    }
    this.db = new Database(this.config.file);
    return this;
  }

  async query(sql, params = []) {
    const stmt = this.db.prepare(sql);
    const rows = stmt.all(...params);
    const fields = rows.length > 0 ? Object.keys(rows[0]) : [];
    return { rows, fields, rowCount: rows.length };
  }

  async getTables(prefix = '') {
    const sql = prefix
      ? `SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '${prefix}%' ORDER BY name`
      : `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`;
    const rows = this.db.prepare(sql).all();
    return rows.map(r => r.name);
  }

  async getColumns(tableName) {
    const rows = this.db.prepare(`PRAGMA table_info(${tableName})`).all();
    return rows.map(r => ({ name: r.name, type: r.type }));
  }

  async getDistinctValues(tableName, columnName, limit = 15) {
    const rows = this.db
      .prepare(`SELECT DISTINCT "${columnName}" FROM "${tableName}" WHERE "${columnName}" IS NOT NULL LIMIT ?`)
      .all(limit);
    return rows.map(r => r[columnName]).filter(Boolean);
  }

  async ping() {
    this.db.prepare('SELECT 1').get();
    return true;
  }

  async disconnect() {
    if (this.db) this.db.close();
  }

  get type() { return 'sqlite'; }
}