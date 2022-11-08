import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Environment } from '../../../environments/environment-variables';
import { map, filter } from 'rxjs/operators';
import { User, UserAdapter } from 'src/app/shared/models/user';
import {
  AcceptanceState,
  AcceptanceStateAdapter,
} from 'src/app/shared/models/acceptanceState';

@Injectable({
  providedIn: 'root',
})
export class ApiAdminService {
  API_URL = Environment.ANGULAR_DJANGO_API_ADMIN_URL;

  constructor(
    private http: HttpClient,
    private userAdapter: UserAdapter,
    private stateAdapter: AcceptanceStateAdapter
  ) {}

  public getUsers(): Observable<User[]> {
    return this.http
      .get<User[]>(`${this.API_URL}/auth/user/`)
      .pipe(
        map((items: any[]) => items.map((item) => this.userAdapter.adapt(item)))
      );
  }

  public getUser(id: string): Observable<User> {
    return this.http
      .get<User>(`${this.API_URL}/auth/user/${id}/`)
      .pipe(map((item) => this.userAdapter.adapt(item)));
  }

  public getStates(): Observable<AcceptanceState[]> {
    // FIXME: does this exist ?
    return this.http
      .get<AcceptanceState[]>(`${this.API_URL}/searchapp/acceptancestate/`)
      .pipe(
        map((items: any[]) =>
          items.map((item) => this.stateAdapter.adapt(item))
        )
      );
  }
}
