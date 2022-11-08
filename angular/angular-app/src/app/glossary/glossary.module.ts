import { NgModule } from '@angular/core';
import { SharedModule } from '../shared/shared.module';
import {
  ConceptDetailComponent,
  ConceptDetailSortableHeaderDirective,
} from './concept-detail/concept-detail.component';
import { ConceptListComponent } from './concept-list/concept-list.component';
import { ConceptDocumentDetailsComponent } from './concept-document-details/concept-document-details.component';
import { GlossaryRoutingModule } from './glossary-routing.module';
import { ChipsModule } from 'primeng/chips';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { OverlayPanelModule } from 'primeng/overlaypanel';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';
import { SelectButtonModule } from 'primeng/selectbutton';
import { TableModule } from 'primeng/table';
import {
  NgbDateAdapter,
  NgbDateNativeAdapter,
} from '@ng-bootstrap/ng-bootstrap';
import { DirectivesModule } from '../directives/directives.module';
import { InputSwitchModule } from 'primeng/inputswitch';
@NgModule({
  declarations: [
    ConceptListComponent,
    ConceptDetailComponent,
    ConceptDetailSortableHeaderDirective,
    ConceptDocumentDetailsComponent,
  ],
  imports: [
    SharedModule,
    ChipsModule,
    ToastModule,
    TooltipModule,
    OverlayPanelModule,
    ConfirmDialogModule,
    SharedModule,
    GlossaryRoutingModule,
    SelectButtonModule,
    DirectivesModule,
    InputSwitchModule,
    TableModule,
  ],
  providers: [
    ConfirmationService,
    { provide: NgbDateAdapter, useClass: NgbDateNativeAdapter },
  ],
})
export class GlossaryModule {}
