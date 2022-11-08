import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Router, ActivatedRoute, ParamMap } from '@angular/router';

import { Document } from '../../shared/models/document';
import { SelectItem } from 'primeng/api/selectitem';
import { IconDefinition } from '@fortawesome/fontawesome-svg-core';
import { faCalendarAlt } from '@fortawesome/free-solid-svg-icons';
import { AcceptanceState } from 'src/app/shared/models/acceptanceState';

import * as uuid from 'uuid';
import {MessageService} from 'primeng/api';

@Component({
  selector: 'app-document-add',
  templateUrl: './document-add.component.html',
  styleUrls: ['./document-add.component.css'],
})
export class DocumentAddComponent implements OnInit {
  websiteId: string;
  document: Document;
  acceptanceState: string;
  allStates: SelectItem[] = [];
  calendarIcon: IconDefinition;
  submitted = false;

  constructor(
    private route: ActivatedRoute,
    private apiService: ApiService,
    private router: Router,
    private messageService: MessageService,
  ) {}

  ngOnInit() {
    this.apiService.getStateValues().subscribe((states) => {
      states.forEach((state) => {
        this.allStates.push({ label: state, value: state });
      });
    });
    this.route.paramMap.subscribe(
      (params: ParamMap) => (this.websiteId = params.get('websiteId'))
    );
    this.document = new Document(
      '',
      '',
      '',
      '',
      new Date(),
      new Date(),
      null,
      null,
      '',
      '',
      '',
      this.websiteId,
      '',
      '',
      '',
      '',
      '',
      '',
      '',
      '',
      '',
      '',
      [],
      [],
      [],
      false,
      '',
      null,
      '',
      [],
      [],
      [],
    );
    this.calendarIcon = faCalendarAlt;
  }

  onAddFile(event) {
    this.document.file = event.files[0];
    this.document.fileUrl = `http://${uuid.v4()}.doc`;
  }

  onSubmit() {
    this.submitted = true;
    let formData = new FormData();
    formData.append('file', this.document.file);
    formData.append('file_url', this.document.fileUrl);
    formData.append('date', this.document.date.toISOString());
    formData.append('title', this.document.title);
    formData.append('url', this.document.url);
    formData.append('website', this.document.website);
    this.apiService.createDocument(formData).subscribe((document) => {
      console.log(document);
      this.apiService
        .updateState(
          new AcceptanceState(
            document.acceptanceState,
            document.id,
            '',
            this.acceptanceState
          )
        )
        .subscribe((state) =>
          this.router.navigate(['/website/' + this.websiteId])
        );
    }, (error) => {
      console.log('ERROR HANDLED: ', error);
      this.submitted = false;
      this.messageService.add({
        severity: 'error',
        summary: 'Validation Error',
        detail: 'This URL has already been added to the sources.',
      });
    });
  }
}
