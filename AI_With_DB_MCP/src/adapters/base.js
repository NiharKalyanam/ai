export class BaseAdapter {
  constructor(config) { this.config = config; }
  async connect() { throw new Error('connect() not implemented'); }
  async query(sql, params = []) { throw new Error('query() not implemented'); }
  async getTables(prefix = '') { throw new Error('getTables() not implemented'); }
  async getColumns(tableName) { throw new Error('getColumns() not implemented'); }
  async getDistinctValues(tableName, columnName, limit = 15) { throw new Error('getDistinctValues() not implemented'); }
  async ping() { throw new Error('ping() not implemented'); }
  async disconnect() {}
  get type() { return 'base'; }
}