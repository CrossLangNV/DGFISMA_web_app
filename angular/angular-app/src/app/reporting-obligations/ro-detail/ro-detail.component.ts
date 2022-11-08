import { Component, OnInit, Directive, Input, Output, EventEmitter, ViewChildren, QueryList } from '@angular/core';
import { ApiService } from 'src/app/core/services/api.service';
import { ActivatedRoute, ParamMap } from '@angular/router';
import { switchMap } from 'rxjs/operators';
import { Document } from 'src/app/shared/models/document';

import { IconDefinition } from '@fortawesome/fontawesome-svg-core';
import {
  faSort,
  faSortUp,
  faSortDown,
  faTrashAlt, faUserAlt, faUserLock, faMicrochip,
} from '@fortawesome/free-solid-svg-icons';
import { Observable, forkJoin } from 'rxjs';
import { ReportingObligation } from 'src/app/shared/models/ro';
import { SelectItem } from 'primeng/api/selectitem';
import { DjangoUser } from '../../shared/models/django_user';
import { AuthenticationService } from '../../core/auth/authentication.service';
import { RoAcceptanceState } from '../../shared/models/roAcceptanceState';
import { MessageService, ConfirmationService } from 'primeng/api';
import { RoComment } from '../../shared/models/roComment';
import { ApiAdminService } from '../../core/services/api.admin.service';

export type SortDirection = 'asc' | 'desc' | '';
const rotate: { [key: string]: SortDirection } = {
  asc: 'desc',
  desc: '',
  '': 'asc',
};

export interface SortEvent {
  column: string;
  direction: SortDirection;
}

@Directive({
  selector: 'th[sortable]',
  host: {
    '[class.asc]': 'direction === "asc"',
    '[class.desc]': 'direction === "desc"',
    '(click)': 'rotate()',
  },
})
export class RoDetailSortableHeaderDirective {
  @Input() sortable: string;
  @Input() direction: SortDirection = '';
  @Output() sortDetail = new EventEmitter<SortEvent>();

  rotate() {
    this.direction = rotate[this.direction];
    this.sortDetail.emit({ column: this.sortable, direction: this.direction });
  }
}

@Component({
  selector: 'app-ro-detail',
  templateUrl: './ro-detail.component.html',
  styleUrls: ['./ro-detail.component.css'],
  providers: [MessageService]
})
export class RoDetailComponent implements OnInit {
  @ViewChildren(RoDetailSortableHeaderDirective) headers: QueryList<
    RoDetailSortableHeaderDirective
  >;
  ro: ReportingObligation;

  occursIn: Document[] = [];
  occursInPage = 1;
  occursInPageSize = 5;
  occursInTotal = 0;
  occursInSortBy = 'date';
  occursInSortDirection = 'desc';
  occursInDateSortIcon: IconDefinition = faSortDown;
  collectionSize = 0;

  definedIn: Document[] = [];
  definedInPage = 1;
  definedInPageSize = 5;
  definedInTotal = 0;
  definedInSortBy = 'date';
  definedInSortDirection = 'desc';
  definedInDateSortIcon: IconDefinition = faSortDown;
  userIcon: IconDefinition;
  userLockIcon: IconDefinition;
  chipIcon: IconDefinition;

  similarRos: ReportingObligation[] = [];

  // AcceptanceState and comments
  stateValues: SelectItem[] = [];
  acceptanceState: RoAcceptanceState;
  comments: RoComment[] = [];
  newComment: RoComment;
  deleteIcon: IconDefinition;
  currentDjangoUser: DjangoUser;

  definitionHtml: string;

  contentHtmlRo = '';

  constructor(
    private route: ActivatedRoute,
    private apiService: ApiService,
    private authenticationService: AuthenticationService,
    private service: ApiService,
    private messageService: MessageService,
    private confirmationService: ConfirmationService,
    private adminService: ApiAdminService,
  ) { }

  ngOnInit() {
    this.userIcon = faUserAlt;
    this.userLockIcon = faUserLock;
    this.chipIcon = faMicrochip;
    this.deleteIcon = faTrashAlt;

    this.authenticationService.currentDjangoUser.subscribe(
      (x) => (this.currentDjangoUser = x)
    );
    this.acceptanceState = new RoAcceptanceState('', '', '', '')
    this.newComment = new RoComment('', '', '', '', new Date(), '');

    this.service.getRoStateValues().subscribe((states) => {
      states.forEach((state) => {
        this.stateValues.push({ label: state, value: state });
      });
    });

    this.route.paramMap
      .pipe(
        switchMap((params: ParamMap) =>
          this.apiService.getRo(params.get('roId'))
        )
      )
      .subscribe((concept) => {
        this.ro = concept;

        this.definitionHtml = this.replaceTerms(concept.definition, [concept]);

        this.newComment.roId = concept.id;
        this.comments = [];

        if (concept.commentIds) {
          concept.commentIds.forEach((commentId) => {
            this.service.getRoComment(commentId).subscribe((comment) => {
              this.comments.push(comment);
            });
          });
        }

        this.loadOccursInDocuments();
        this.loadSimilarROs();
        console.log(this.similarRos)
      });
  }

  loadSimilarROs() {
    this.similarRos = [];
    this.service.getSimilarROs(this.ro.id).subscribe((result) => {
      this.similarRos = result.results;
    });
  }

  loadOccursInDocuments() {
    this.service
      .getDjangoAndSolrPrAnalyzedDocumentsFromRO(
        this.occursInPage,
        this.occursInPageSize,
        this.ro.name,
        'ro_highlight',
        this.ro.id,
        [],
        this.occursInSortBy,
        this.occursInSortDirection
      )
      .subscribe((data) => {
        this.occursInTotal = data[0];
        // const solrDocuments = data[1];
        this.occursIn = data[1];

        // Fallback method
        // if (this.occursIn[0]['ro_highlight'] == null) {
        //   this.occursIn[0]['ro_highlight'] = this.highlight(this.ro.name, this.ro);
        // }

        if (this.occursIn[0]) {
          // Load HTML from a single reporting obligation
          this.service.getReportingObligationsViewSingle(
            this.ro.name,
            this.occursIn[0].id
          ).subscribe((response) => {
            this.contentHtmlRo = response
          });
        }
      });
  }

  // loadOccursInDocuments() {
  //   this.service
  //     .searchSolrPreAnalyzedDocuments(
  //       this.occursInPage,
  //       this.occursInPageSize,
  //       this.ro.name,
  //       'ro_highlight',
  //       [],
  //       this.occursInSortBy,
  //       this.occursInSortDirection
  //     )
  //     .subscribe((data) => {
  //       this.occursInTotal = data[0];
  //       // const solrDocuments = data[1];
  //       this.occursIn = data[1];
  //
  //       if (this.occursIn) {
  //         // Load HTML from a single reporting obligation
  //         this.service.getReportingObligationsViewSingle(
  //           this.ro.name,
  //           this.occursIn[0].id
  //         ).subscribe((response) => {
  //           this.contentHtmlRo = response
  //         });
  //       }
  //     });
  // }

  getDocuments(ids: string[]): Observable<any[]> {
    const docObservables = [];
    ids.forEach((id) => {
      docObservables.push(this.apiService.getDocument(id));
    });
    return forkJoin(docObservables);
  }

  loadOccursInPage(page: number) {
    this.occursInPage = page;
    this.loadOccursInDocuments();
  }

  onSortOccursIn({ column, direction }: SortEvent) {
    // resetting other headers
    this.headers.forEach((header) => {
      if (header.sortable !== column) {
        header.direction = '';
      }
    });

    // sorting occursIn, default date descending
    if (direction === '') {
      this.occursInSortBy = 'date';
      this.occursInSortDirection = 'desc';
      this.occursInDateSortIcon = faSortDown;
      this.loadOccursInDocuments();
    } else {
      this.occursInSortDirection = direction;
      this.occursInSortBy = column;
      const sortIcon = direction === 'asc' ? faSortUp : faSortDown;
      if (column === 'date') {
        this.occursInDateSortIcon = sortIcon;
      } else {
        this.occursInDateSortIcon = faSort;
      }
      this.loadOccursInDocuments();
    }
  }

  onStateChange(event) {
    // FIXME: can we abract the the acceptanceState.id  via the API (should not be know externally ?)
    this.acceptanceState.id = this.ro.acceptanceState;
    this.acceptanceState.value = event.value;
    this.acceptanceState.roId = this.ro.id;
    this.service.updateRoState(this.acceptanceState).subscribe((result) => {
      // Update document list
      this.service.messageSource.next('refresh');
      const severity = {
        Accepted: 'success',
        Rejected: 'error',
        Unvalidated: 'info',
      };
      this.messageService.add({
        severity: severity[event.value],
        summary: 'Acceptance State',
        detail: 'Set to "' + event.value + '"',
      });
    });
  }

  onAddComment() {
    this.service.addRoComment(this.newComment).subscribe((comment) => {
      comment.username = this.currentDjangoUser.username;
      this.comments.push(comment);
      this.newComment.value = '';
      this.service.messageSource.next('refresh');
    });
  }

  onDeleteComment(comment: RoComment) {
    this.confirmationService.confirm({
      message: 'Do you want to delete this comment?',
      accept: () => {
        this.service.deleteRoComment(comment.id).subscribe((response) => {
          this.comments = this.comments.filter(
            (item) => item.id !== comment.id
          );
          this.service.messageSource.next('refresh');
        });
      },
    });
  }

  replaceTerms(definition, terms) {
    terms.forEach(term => {
      definition = this.highlight(definition, term)
    });
    return definition;
  }

  highlight(definition: string, concept): String {
    const searchMask = this.escapeRegex(concept.name);
    const regEx = new RegExp(searchMask, 'ig');
    const replaceMask = '<span class="highlight">' + concept.name + '</span>';
    return definition.replace(regEx, replaceMask);
  }

  escapeRegex(string: string) {
    return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
  }

  containsGroup(groups: Array<any>, groupName: string) {
    return groups.some((group) => group.name === groupName);
  }
}

