import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { DjangoUser } from '../../shared/models/django_user';
import { Environment } from '../../../environments/environment-variables';
import { SocialUser } from 'angularx-social-login';

@Injectable({ providedIn: 'root' })
export class AuthenticationService {
  private currentDjangoUserSubject: BehaviorSubject<DjangoUser>;
  public currentDjangoUser: Observable<DjangoUser>;

  constructor(private http: HttpClient) {
    this.currentDjangoUserSubject = new BehaviorSubject<DjangoUser>(
      JSON.parse(localStorage.getItem('currentDjangoUser'))
    );
    this.currentDjangoUser = this.currentDjangoUserSubject.asObservable();
  }

  public get currentDjangoUserValue(): DjangoUser {
    return this.currentDjangoUserSubject.value;
  }

  login(username, password) {
    let client_id = Environment.ANGULAR_DJANGO_CLIENT_ID;
    let client_secret = Environment.ANGULAR_DJANGO_CLIENT_SECRET;
    return this.http
      .post<any>(`${Environment.ANGULAR_DJANGO_AUTH_URL}/token`, {
        client_id,
        client_secret,
        username,
        password,
        grant_type: 'password'
      })
      .pipe(
        map(djangoUser => {
          djangoUser.username = username;
          // store user details and token in local storage to keep user logged in between page refreshes
          localStorage.setItem('currentDjangoUser', JSON.stringify(djangoUser));
          this.currentDjangoUserSubject.next(djangoUser);
          return djangoUser;
        })
      );
  }

  signInWithGoogle(userData: SocialUser) {
    let client_id = Environment.ANGULAR_DJANGO_CLIENT_ID;
    let client_secret = Environment.ANGULAR_DJANGO_CLIENT_SECRET;
    return this.http
      .post<any>(`${Environment.ANGULAR_DJANGO_AUTH_URL}/convert-token`, {
        client_id,
        client_secret,
        backend: 'google-oauth2',
        token: userData.authToken,
        grant_type: 'convert_token'
      })
      .pipe(
        map(djangoUser => {
          djangoUser.username = userData.email;
          // store user details and token in local storage to keep user logged in between page refreshes
          localStorage.setItem(
            'currentDjangoUser',
            JSON.stringify(djangoUser)
          );
          this.currentDjangoUserSubject.next(djangoUser);
          return djangoUser;
        })
      );
  }

  logout() {
    // remove user from local storage and set current user to null
    localStorage.removeItem('currentDjangoUser');
    this.currentDjangoUserSubject.next(null);
  }
}
