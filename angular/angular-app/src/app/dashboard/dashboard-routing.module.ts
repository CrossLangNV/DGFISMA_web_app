import { Routes, RouterModule } from '@angular/router';
import { UserListComponent } from './user-list/user-list.component';

const routes: Routes = [
  {
    path: '',
    data: {
      breadcrumb: 'Dashboard'
    },
    children: [
      {
        path: '',
        component: UserListComponent
      }
    ]
  }
];

export const DashboardRoutingModule = RouterModule.forChild(routes);
