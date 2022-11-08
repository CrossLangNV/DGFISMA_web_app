import { Routes, RouterModule } from '@angular/router';
import { RoListComponent } from './ro-list/ro-list.component';
import { RoDetailComponent } from './ro-detail/ro-detail.component';
import { RoDocumentDetailsComponent } from './ro-document-details/ro-document-details.component';

const routes: Routes = [
  {
    path: 'ro',
    data: {
      breadcrumb: 'Reporting Obligations',
    },
    children: [
      {
        path: '',
        component: RoListComponent,
        children: [
          {
            path: ':roId',
            component: RoDetailComponent,
          },
        ],
      },
    ],
  },
  {
    path: 'ro/document',
    data: {
      breadcrumb: 'Reporting Obligations',
    },
    children: [
      {
        path: ':roId/:documentId',
        component: RoDocumentDetailsComponent,
      },
    ],
  },
];

export const RoRoutingModule = RouterModule.forChild(routes);
