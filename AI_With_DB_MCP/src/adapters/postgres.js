import pg from 'pg';
import { BaseAdapter } from './base.js';

const { Pool } = pg;

export class PostgresAdapter extends BaseAdapter {
  constructor(config) {
    super(config);
    this.pool = null;
  }

  async connect() {
    this.pool = new Pool({
      host: this.config.host,
      port: this.config.port,
      database: this.config.name,
      user: this.config.user,
      password: this.config.password,
      max: this.config.connectionLimit || 10,
    });
    await this.ping();
    return this;
  }

  async query(sql, params = []) {
    const result = await this.pool.query(sql, params);
    return {
      rows: result.rows,
      fields: result.fields.map(f => f.name),
      rowCount: result.rowCount,
    };
  }

  async getTables(prefix = '') {
    const sql = prefix
      ? `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE $1 ORDER BY table_name`
      : `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name`;
    const params = prefix ? [`${prefix}%`] : [];
    const result = await this.pool.query(sql, params);
    return result.rows.map(r => r.table_name);
  }

  async getColumns(tableName) {
    const result = await this.pool.query(
      `SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1 ORDER BY ordinal_position`,
      [tableName]
    );
    return result.rows.map(r => ({ name: r.column_name, type: r.data_type }));
  }

  async getDistinctValues(tableName, columnName, limit = 15) {
    const result = await this.pool.query(
      `SELECT DISTINCT "${columnName}" FROM "${tableName}" WHERE "${columnName}" IS NOT NULL LIMIT $1`,
      [limit]
    );
    return result.rows.map(r => r[columnName]).filter(Boolean);
  }

  async ping() {
    await this.pool.query('SELECT 1');
    return true;
  }

  async disconnect() {
    if (this.pool) await this.pool.end();
  }

  get type() { return 'postgres'; }
}
