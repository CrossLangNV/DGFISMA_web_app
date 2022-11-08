import { Routes, RouterModule } from '@angular/router';
import { ConceptListComponent } from './concept-list/concept-list.component';
import { ConceptDetailComponent } from './concept-detail/concept-detail.component';
import { ConceptDocumentDetailsComponent } from './concept-document-details/concept-document-details.component';

const routes: Routes = [
  {
    path: 'glossary',
    data: {
      breadcrumb: 'Concepts',
    },
    children: [
      {
        path: '',
        component: ConceptListComponent,
        children: [
          {
            path: ':conceptId',
            component: ConceptDetailComponent,
          },
        ],
      },
    ],
  },
  {
    path: 'document',
    data: {
      breadcrumb: null,
    },
    children: [
      {
        path: ':annotationType/:conceptId/:documentId',
        component: ConceptDocumentDetailsComponent,
      },
    ],
  },
];

export const GlossaryRoutingModule = RouterModule.forChild(routes);
