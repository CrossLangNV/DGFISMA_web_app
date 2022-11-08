import { Component } from '@angular/core';
import { Router } from '@angular/router';

import { AuthenticationService } from './core/auth/authentication.service';
import { DjangoUser } from './shared/models/django_user';
import { ApiService } from './core/services/api.service';

@Component({ selector: 'app', templateUrl: 'app.component.html' })
export class AppComponent {
  currentDjangoUser: DjangoUser;
  adminMode = false;
  app_version = 'uknown version';

  constructor(
    private router: Router,
    private apiService: ApiService,
    private authenticationService: AuthenticationService
  ) {
    this.authenticationService.currentDjangoUser.subscribe(
      (x) => (this.currentDjangoUser = x)
    );
    if (this.apiService.APP_VERSION) {
      this.app_version = this.apiService.APP_VERSION;
    }
  }

  logout() {
    this.authenticationService.logout();
    this.router.navigate(['/login']);
  }
}
