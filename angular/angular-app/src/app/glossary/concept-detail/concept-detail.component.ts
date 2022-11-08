import {
  Component,
  OnInit,
  Directive,
  Input,
  Output,
  EventEmitter,
  ViewChildren,
  QueryList,
} from '@angular/core';
import { ApiService } from 'src/app/core/services/api.service';
import { ActivatedRoute, ParamMap } from '@angular/router';
import { switchMap } from 'rxjs/operators';
import { Concept } from 'src/app/shared/models/concept';
import { Document } from 'src/app/shared/models/document';

import { IconDefinition } from '@fortawesome/fontawesome-svg-core';
import {
  faSort,
  faSortUp,
  faSortDown,
  faTrashAlt, faUserAlt, faUserLock, faMicrochip,
} from '@fortawesome/free-solid-svg-icons';
import { Observable, forkJoin } from 'rxjs';
import { SelectItem } from 'primeng/api/selectitem';
import { ConceptAcceptanceState } from '../../shared/models/conceptAcceptanceState';
import { ConceptComment } from '../../shared/models/conceptComment';
import { ApiAdminService } from '../../core/services/api.admin.service';
import { MessageService, ConfirmationService } from 'primeng/api';
import { DjangoUser } from '../../shared/models/django_user';
import { AuthenticationService } from '../../core/auth/authentication.service';

export type SortDirection = 'asc' | 'desc' | '';
const rotate: { [key: string]: SortDirection } = {
  asc: 'desc',
  desc: '',
  '': 'asc',
};

const NODE_TYPE_TEXT_NODE = 3;

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
export class ConceptDetailSortableHeaderDirective {
  @Input() sortable: string;
  @Input() direction: SortDirection = '';
  @Output() sortDetail = new EventEmitter<SortEvent>();

  rotate() {
    this.direction = rotate[this.direction];
    this.sortDetail.emit({ column: this.sortable, direction: this.direction });
  }
}

@Component({
  selector: 'app-concept-detail',
  templateUrl: './concept-detail.component.html',
  styleUrls: ['./concept-detail.component.css'],
  providers: [MessageService],
})
export class ConceptDetailComponent implements OnInit {
  @ViewChildren(ConceptDetailSortableHeaderDirective)
  headers: QueryList<ConceptDetailSortableHeaderDirective>;
  concept: Concept;

  // AcceptanceState and comments
  stateValues: SelectItem[] = [];
  acceptanceState: ConceptAcceptanceState;
  comments: ConceptComment[] = [];
  newComment: ConceptComment;
  deleteIcon: IconDefinition;
  currentDjangoUser: DjangoUser;
  definitionHtml: string;

  occursIn: Document[] = [];
  occursInPage = 1;
  occursInPageSize = 5;
  occursInTotal = 0;
  occursInSortBy = 'date';
  occursInSortDirection = 'desc';
  occursInDateSortIcon: IconDefinition = faSortDown;

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

  constructor(
    private route: ActivatedRoute,
    private service: ApiService,
    private adminService: ApiAdminService,
    private messageService: MessageService,
    private authenticationService: AuthenticationService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit() {
    this.userIcon = faUserAlt;
    this.userLockIcon = faUserLock;
    this.chipIcon = faMicrochip;
    this.deleteIcon = faTrashAlt;
    this.authenticationService.currentDjangoUser.subscribe(
      (x) => (this.currentDjangoUser = x)
    );
    this.acceptanceState = new ConceptAcceptanceState('', '', '', '');
    this.newComment = new ConceptComment('', '', '', '', new Date(), '');

    this.service.getConceptStateValues().subscribe((states) => {
      states.forEach((state) => {
        this.stateValues.push({ label: state, value: state });
      });
    });

    this.route.paramMap
      .pipe(
        switchMap((params: ParamMap) =>
          this.service.getConcept(params.get('conceptId'))
        )
      )
      .subscribe((concept) => {
        this.concept = concept;

        this.definitionHtml = this.replaceTerms(
          concept.definition,
          [concept],
          'highlight'
        );
        this.definitionHtml = this.replaceTerms(
          this.definitionHtml,
          concept.other,
          'highlight-secondary'
        );

        this.newComment.conceptId = concept.id;
        this.comments = [];

        if (concept.commentIds) {
          concept.commentIds.forEach((commentId) => {
            this.service.getConceptComment(commentId).subscribe((comment) => {
              this.comments.push(comment);
            });
          });
        }

        this.loadOccursInDocuments();
        this.loadDefinedInDocuments();
      });

  }

  onStateChange(event) {
    this.acceptanceState.value = event.value;
    this.acceptanceState.conceptId = this.concept.id;
    this.service
      .updateConceptState(this.acceptanceState)
      .subscribe((result) => {
        // Update document list
        this.service.messageSource.next('refresh');
        let severity = {
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
    this.service.addConceptComment(this.newComment).subscribe((comment) => {
      comment.username = this.currentDjangoUser.username;
      this.comments.push(comment);
      this.newComment.value = '';
      this.service.messageSource.next('refresh');
    });
  }

  onDeleteComment(comment: ConceptComment) {
    this.confirmationService.confirm({
      message: 'Do you want to delete this comment?',
      accept: () => {
        this.service.deleteConceptComment(comment.id).subscribe((response) => {
          this.comments = this.comments.filter(
            (item) => item.id !== comment.id
          );
          this.service.messageSource.next('refresh');
        });
      },
    });
  }

  loadOccursInDocuments() {

    let page = 0;
    if (this.occursInPage === 1 ) {
      page = 0
    } else {
      page = (this.occursInPage * this.occursInPageSize) - this.occursInPageSize;
    }

    this.service
      .getConceptOccurrences(
        page,
        this.occursInPageSize,
        this.concept.id,
        this.occursInSortBy,
        this.occursInSortDirection
      )
      .subscribe((data) => {
        // @ts-ignore
        this.occursIn = data.results;
        // @ts-ignore
        this.occursInTotal = data.count;
      });
  }

  loadDefinedInDocuments() {
    this.service
      .getDjangoAndSolrPrAnalyzedDocuments(
        this.definedInPage,
        this.definedInPageSize,
        this.concept.definition,
        'concept_defined',
        this.concept.id,
        [],
        this.definedInSortBy,
        this.definedInSortDirection
      )
      .subscribe((data) => {
        this.definedInTotal = data[0];
        this.definedIn = data[1];

        // Fallback method
        if (this.definedIn[0]['concept_defined'] == null) {
          this.definedIn[0]['concept_defined'] = this.highlight(this.concept.definition, this.concept);
        }
      });
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

  getDocuments(ids: string[]): Observable<any[]> {
    let docObservables = [];
    ids.forEach((id) => {
      docObservables.push(this.service.getDocument(id));
    });
    return forkJoin(docObservables);
  }

  loadOccursInPage(page: number) {
    this.occursInPage = page;
    this.loadOccursInDocuments();
  }

  loadDefinedInPage(page: number) {
    this.definedInPage = page;
    this.loadDefinedInDocuments();
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

  onSortDefinedIn({ column, direction }: SortEvent) {
    // resetting other headers
    this.headers.forEach((header) => {
      if (header.sortable !== column) {
        header.direction = '';
      }
    });

    // sorting definedIn, default date descending
    if (direction === '') {
      this.definedInSortBy = 'date';
      this.definedInSortDirection = 'desc';
      this.definedInDateSortIcon = faSortDown;
      this.loadDefinedInDocuments();
    } else {
      this.definedInSortDirection = direction;
      this.definedInSortBy = column;
      const sortIcon = direction === 'asc' ? faSortUp : faSortDown;
      if (column === 'date') {
        this.definedInDateSortIcon = sortIcon;
      } else {
        this.definedInDateSortIcon = faSort;
      }
      this.loadDefinedInDocuments();
    }
  }

  replaceTerms(definition, concepts, cssClass) {
    concepts.forEach((concept) => {
      definition = this.highlightInHtml(definition, concept, cssClass);
    });
    return definition;
  }

  highlightInHtml(definition, concept, className): String {
    var parser = new DOMParser();
    var definitionDocument = parser.parseFromString(definition, 'text/html');
    this.highlightInNodesTree(definitionDocument, concept, className);
    return definitionDocument.body.innerHTML;
  }

  highlightInNodesTree(node, concept, className) {
    if (node.nodeType == NODE_TYPE_TEXT_NODE) {
      var text = node.nodeValue;
      var fragment = this.injectSpansWithClass(text, concept.name, className);
      var parentNode = node.parentNode;
      parentNode.replaceChild(fragment, node);
    }
    else if (node.childNodes != null && !this.nodeIsHighlighted(node)) {
      for (var i = 0; i < node.childNodes.length; i++) {
        this.highlightInNodesTree(node.childNodes[i], concept, className);
      }
    }
  }

  nodeIsHighlighted(node) {
    if (node.nodeName != "SPAN") {
      return false;
    }
    else if (node.classList.contains("highlight") || node.classList.contains("highlight-secondary")) {
      return true;
    }
    return false;
  }

  addSpanWithClass(str, className) {
    var span = document.createElement("span");
    span.className = className;
    span.appendChild(document.createTextNode(str));
    return span;
  }

  injectSpansWithClass(str, partToWrap, className) {
    var splitParts = this.splitLowercased(str, partToWrap);
    var offset = 0;
    var fragment = document.createDocumentFragment();
    for (var i = 0; i < splitParts.length; i++) {
      var normalCasedSplitPart = str.substring(offset, offset + splitParts[i].length);
      fragment.appendChild(document.createTextNode(normalCasedSplitPart));
      offset += splitParts[i].length;
      if (i < splitParts.length || this.endsWithCaseInsensitive(str, partToWrap)) {
        var normalCasedPartToWrap = str.substring(offset, offset + partToWrap.length);
        fragment.appendChild(this.addSpanWithClass(normalCasedPartToWrap, className));
        offset += partToWrap.length;
      }
    }
    return fragment;
  }

  startsWithCaseInsensitive(str, possibleStart) {
    str = str.toLowerCase();
    possibleStart = possibleStart.toLowerCase();
    return str.startsWith(possibleStart);
  }

  endsWithCaseInsensitive(str, possibleEnd) {
    str = str.toLowerCase();
    possibleEnd = possibleEnd.toLowerCase();
    return str.startsWith(possibleEnd);
  }

  splitLowercased(str, separator) {
    str = str.toLowerCase();
    separator = separator.toLowerCase();
    return str.split(separator);
  }

  containsGroup(groups: Array<any>, groupName: string) {
    return groups.some((group) => group.name === groupName);
  }
}
