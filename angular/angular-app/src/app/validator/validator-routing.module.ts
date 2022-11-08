import { Routes, RouterModule } from '@angular/router';
import { DocumentListComponent } from './document-list/document-list.component';
import { DocumentValidateComponent } from './document-validate/document-validate.component';

const routes: Routes = [
  {
    path: '',
    data: {
      breadcrumb: 'Dashboard',
    },
    children: [
      {
        path: '',
        component: DocumentListComponent,
        children: [
          {
            path: ':documentId',
            component: DocumentValidateComponent,
          },
        ],
      },
    ],
  },
];

export const ValidatorRoutingModule = RouterModule.forChild(routes);
