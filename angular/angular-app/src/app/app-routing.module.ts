import { Routes, RouterModule } from '@angular/router';

import { LoginComponent } from './shared/login-component/login.component';
import { AuthGuard } from './core/guards/auth.guard';
import { GlossaryModule } from './glossary/glossary.module';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', redirectTo: '/validator', pathMatch: 'full' },
  {
    path: 'browse',
    loadChildren: () =>
      import('./browse/browse.module').then((m) => m.BrowseModule),
    canActivate: [AuthGuard],
  },
  {
    path: 'glossary',
    loadChildren: () =>
      import('./glossary/glossary.module').then((m) => m.GlossaryModule),
    canActivate: [AuthGuard],
  },
  {
    path: 'document',
    loadChildren: () =>
      import('./directives/directives.module').then((m) => m.DirectivesModule),
    canActivate: [AuthGuard],
  },
  {
    path: 'dashboard',
    loadChildren: () =>
      import('./dashboard/dashboard.module').then((m) => m.DashboardModule),
    canActivate: [AuthGuard],
  },
  {
    path: 'validator',
    loadChildren: () =>
      import('./validator/validator.module').then((m) => m.ValidatorModule),
    canActivate: [AuthGuard],
  },

  // otherwise redirect to home
  { path: '**', redirectTo: '/validator' },
];

export const AppRoutingModule = RouterModule.forRoot(routes);
