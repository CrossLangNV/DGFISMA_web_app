import { NgModule } from '@angular/core';
import { SharedModule } from '../shared/shared.module';
import {
  RoDetailComponent,
  RoDetailSortableHeaderDirective,
} from './ro-detail/ro-detail.component';
import {
  RoListComponent,
  NgbdSortableHeaderDirective,
} from './ro-list/ro-list.component';
import { RoDocumentDetailsComponent } from './ro-document-details/ro-document-details.component';
import { RoRoutingModule } from './reporting-obligations-routing.module';
import { ChipsModule } from 'primeng/chips';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { OverlayPanelModule } from 'primeng/overlaypanel';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';
import {
  NgbDateAdapter,
  NgbDateNativeAdapter,
} from '@ng-bootstrap/ng-bootstrap';
import { DropdownModule } from 'primeng/dropdown';
import { FieldsetModule } from 'primeng/fieldset';
import {PanelModule} from 'primeng/panel';
import {MenuModule} from 'primeng/menu';
import { SelectButtonModule } from 'primeng/selectbutton';
import {NgxSkeletonLoaderModule} from 'ngx-skeleton-loader';
import { DirectivesModule } from '../directives/directives.module';
import { RoBreakdownComponent } from './ro-breakdown/ro-breakdown.component';
import {TableModule} from 'primeng/table';
import {AutoCompleteModule} from 'primeng/autocomplete';
import { RoBreakdownSingleComponent } from './ro-breakdown-single/ro-breakdown-single.component';
import {InputSwitchModule} from 'primeng/inputswitch';

@NgModule({
    declarations: [
        RoListComponent,
        RoDetailComponent,
        NgbdSortableHeaderDirective,
        RoDetailSortableHeaderDirective,
        RoDocumentDetailsComponent,
        RoBreakdownComponent,
        RoBreakdownComponent,
        RoBreakdownSingleComponent
    ],
    imports: [
        SharedModule,
        ChipsModule,
        ToastModule,
        TooltipModule,
        OverlayPanelModule,
        ConfirmDialogModule,
        SharedModule,
        RoRoutingModule,
        DropdownModule,
        FieldsetModule,
        PanelModule,
        MenuModule,
        SelectButtonModule,
        NgxSkeletonLoaderModule.forRoot(),
        DirectivesModule,
        TableModule,
        AutoCompleteModule,
        InputSwitchModule,
    ],
  providers: [
    ConfirmationService,
    { provide: NgbDateAdapter, useClass: NgbDateNativeAdapter },
  ],
})
export class ReportingObligationsModule {}
