import { Routes, RouterModule } from '@angular/router';
import { WebsiteListComponent } from './website-list/website-list.component';
import { WebsiteDetailsComponent } from './website-details/website-details.component';
import { DocumentDetailsComponent } from './document-details/document-details.component';
import { WebsiteAddComponent } from './website-add/website-add.component';
import { DocumentAddComponent } from './document-add/document-add.component';

const routes: Routes = [
  { path: 'browse', redirectTo: '/browse/website', pathMatch: 'full' },
  {
    path: 'website',
    data: {
      breadcrumb: 'Sources',
    },
    children: [
      {
        path: '',
        component: WebsiteListComponent,
      },
      {
        path: 'add',
        component: WebsiteAddComponent,
        data: {
          breadcrumb: 'Add',
        },
      },
      {
        path: ':websiteId',
        data: {
          breadcrumb: '',
        },
        children: [
          {
            path: '',
            component: WebsiteDetailsComponent,
          },
          {
            path: 'add',
            component: DocumentAddComponent,
            data: {
              breadcrumb: 'Add',
            },
          },
          {
            path: 'document/:documentId',
            data: {
              breadcrumb: '',
            },
            component: DocumentDetailsComponent,
          },
        ],
      },
    ],
  },
];

export const BrowseRoutingModule = RouterModule.forChild(routes);
