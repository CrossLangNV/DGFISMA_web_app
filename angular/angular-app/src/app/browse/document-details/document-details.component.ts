import { Component, OnInit } from '@angular/core';
import { Document } from 'src/app/shared/models/document';
import { IconDefinition } from '@fortawesome/fontawesome-svg-core';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { ApiService } from 'src/app/core/services/api.service';
import { switchMap } from 'rxjs/operators';
import { faTrashAlt } from '@fortawesome/free-solid-svg-icons';
import { Attachment } from 'src/app/shared/models/attachment';
import { SelectItem, ConfirmationService } from 'primeng/api';
import * as uuid from 'uuid';
import { AcceptanceState } from 'src/app/shared/models/acceptanceState';

@Component({
  selector: 'app-document-details',
  templateUrl: './document-details.component.html',
  styleUrls: ['./document-details.component.css'],
})
export class DocumentDetailsComponent implements OnInit {
  websiteId: string;
  document: Document;
  deleteIcon: IconDefinition;
  attachments: Attachment[] = [];
  stateValues: SelectItem[] = [];
  acceptanceState: AcceptanceState;

  constructor(
    private route: ActivatedRoute,
    private apiService: ApiService,
    private router: Router,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit() {
    this.acceptanceState = new AcceptanceState('', '', '', '');
    this.apiService.getStateValues().subscribe((states) => {
      states.forEach((state) => {
        this.stateValues.push({ label: state, value: state });
      });
    });
    this.route.paramMap.subscribe(
      (params: ParamMap) => (this.websiteId = params.get('websiteId'))
    );
    this.route.paramMap
      .pipe(
        switchMap((params: ParamMap) =>
          this.apiService.getDocumentSyncWithAttachments(
            params.get('documentId')
          )
        )
      )
      .subscribe((document) => {
        this.document = document;
        document.attachments.forEach((attachment) => {
          this.apiService
            .getAttachment(attachment.id)
            .subscribe((attachment) => {
              this.attachments.push(attachment);
            });
        });
        this.apiService
          .getState(document.acceptanceState)
          .subscribe((state) => {
            this.acceptanceState = state;
          });
      });
    this.deleteIcon = faTrashAlt;
  }

  onStateChange(event) {
    this.acceptanceState.value = event.value;
    this.acceptanceState.documentId = this.document.id;
    this.apiService.updateState(this.acceptanceState).subscribe();
  }

  onAddFile(event) {
    const newFile = event.files[0];
    const formData = new FormData();
    formData.append('document', this.document.id);
    formData.append('file', newFile);
    formData.append('url', `http://${uuid.v4()}.test`);
    this.apiService.addAttachment(formData).subscribe((attachment) => {
      this.router
        .navigateByUrl('/website', { skipLocationChange: true })
        .then(() =>
          this.router.navigate([
            '/website',
            this.websiteId,
            'document',
            this.document.id,
          ])
        );
    });
  }

  onDelete() {
    this.confirmationService.confirm({
      message: 'Do you want to delete this document?',
      accept: () => {
        this.apiService
          .deleteDocument(this.document.id)
          .subscribe((document) =>
            this.router.navigate(['/website/' + this.websiteId])
          );
      },
    });
  }

  onDeleteAttachment(attachment: Attachment) {
    this.confirmationService.confirm({
      message: `Do you want to delete ${attachment.file}?`,
      accept: () => {
        this.apiService
          .deleteAttachment(attachment.id)
          .subscribe((attachment) =>
            this.router
              .navigateByUrl('/website', { skipLocationChange: true })
              .then(() =>
                this.router.navigate([
                  '/website',
                  this.websiteId,
                  'document',
                  this.document.id,
                ])
              )
          );
      },
    });
  }
}
