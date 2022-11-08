import { Injectable } from '@angular/core';
import { Adapter } from './adapter';
import {AcceptanceState} from './acceptanceState';
export interface DbQueryResults {
  count: number;
  next: string;
  previous: string;
  results: DbQuery[];
}
export class DbQuery {
  constructor(
    public id: string,
    public query: string,
    public rdf_query: string,
    public app: string,
    public user: string,
    public created_at: string,
  ) {}
}
@Injectable({
  providedIn: 'root',
})
export class DbQueryAdapter implements Adapter<DbQuery> {
  adapt(item: any): DbQuery {
    return new DbQuery(
      item.id,
      item.query,
      item.rdf_query,
      item.app,
      item.user,
      item.created_at,
    );
  }
  encode(dbQuery: DbQuery): any {
    return {
      id: dbQuery.id,
      query: dbQuery.query,
      rdf_query: dbQuery.rdf_query,
      app: dbQuery.app,
      user: dbQuery.user,
      created_at: dbQuery.created_at,
    };
  }
}
