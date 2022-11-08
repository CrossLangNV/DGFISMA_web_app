import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { IconDefinition } from '@fortawesome/fontawesome-svg-core';
import {
  faCheck, faCross,
  faMicrochip,
  faStar,
  faStopCircle,
  faSyncAlt, faTimes,
  faUserAlt,
  faUserLock,
} from '@fortawesome/free-solid-svg-icons';
import { from } from 'rxjs';
import { AuthenticationService } from 'src/app/core/auth/authentication.service';
import { ApiService } from 'src/app/core/services/api.service';
import { DocumentService } from 'src/app/core/services/document.service';
import { DjangoUser } from 'src/app/shared/models/django_user';
import { Document } from 'src/app/shared/models/document';
import { Tag } from 'src/app/shared/models/tag';
import { DropdownOption } from '../../shared/models/DropdownOption';
import { SelectItem } from 'primeng/api/selectitem';
import { LazyLoadEvent } from 'primeng/api/lazyloadevent';
import { AcceptanceState } from 'src/app/shared/models/acceptanceState';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { Subject } from 'rxjs';
import {ConfirmationService} from 'primeng/api';
import {ConfirmDialogModule} from 'primeng/confirmdialog';
import {ApiAdminService} from '../../core/services/api.admin.service';


@Component({
  selector: 'app-document-list',
  templateUrl: './document-list.component.html',
  styleUrls: ['./document-list.component.css'],
})
export class DocumentListComponent implements OnInit {
  // documentResults$: Observable<DocumentResults>;
  documents: Document[];
  selectedDocuments: Document[] = [];
  selectedId: number;
  offset = 0;
  rows = 5;
  collectionSize = 0;
  data1: any;
  data2: any;
  action = 'none';
  options1 = {
    title: {
      display: true,
      text: 'Auto classification',
      fontSize: 16,
    },
    legend: {
      position: 'bottom',
    },
  };
  options2 = {
    title: {
      display: true,
      text: 'Human classification',
      fontSize: 16,
    },
    legend: {
      position: 'bottom',
    },
  };
  filterActive = false;
  stats = {
    classifiedSize: 0,
    classifiedPercent: 0,
    unvalidatedSize: 0,
    unvalidatedPercent: 0,
    acceptedSize: 0,
    acceptedPercent: 0,
    rejectedSize: 0,
    rejectedPercent: 0,
    autoClassifiedSize: 0,
    autoClassifiedPercent: 0,
    autoUnvalidatedSize: 0,
    autoUnvalidatedPercent: 0,
    autoAcceptedSize: 0,
    autoAcceptedPercent: 0,
    autoRejectedSize: 0,
    autoRejectedPercent: 0,
    totalDocuments: 0,
  };
  userIcon: IconDefinition;
  userLockIcon: IconDefinition;
  chipIcon: IconDefinition;
  reloadIcon: IconDefinition = faSyncAlt;
  resetIcon: IconDefinition = faStopCircle;
  acceptedIcon: IconDefinition = faCheck;
  rejectedIcon: IconDefinition = faTimes;
  bookmarkIcon: IconDefinition = faStar;
  filters = [
    { id: '', name: 'Acceptance state..' },
    { id: 'unvalidated', name: '..Unvalidated' },
    { id: 'accepted', name: '..Accepted' },
    { id: 'rejected', name: '..Rejected' },
  ];
  websites = [{ id: '', name: 'Website..' }];
  usersFilter = [
      { id: '', name: 'Validated by..' },
      { id: 'auto-classifier', name: '..Auto-classifier' },
  ];
  currentDjangoUser: DjangoUser;
  selectedIndex: string = null;
  stateValues: SelectItem[] = [];
  ranInit: boolean = false;
  searchTermChanged: Subject<string> = new Subject<string>();

  celexOptions: DropdownOption[];
  typeOptions: DropdownOption[];
  statusOptions: DropdownOption[];
  eliOptions: DropdownOption[];
  authorOptions: DropdownOption[];
  effectDateOptions: DropdownOption[];

  selectedCelex: string;
  selectedType: string;
  selectedStatus: string;
  selectedEli: string;
  selectedAuthor: string;
  selectedEffectDate: string;

  first = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private service: ApiService,
    public documentService: DocumentService,
    private authenticationService: AuthenticationService,
    private confirmationService: ConfirmationService,
  ) {}

  ngOnInit() {
    this.userIcon = faUserAlt;
    this.userLockIcon = faUserLock;
    this.chipIcon = faMicrochip;
    this.authenticationService.currentDjangoUser.subscribe((x) => {
      this.currentDjangoUser = x;
      this.documentService.username = x.username;
    });
    this.service.getWebsites().subscribe((websites) => {
      websites.forEach((website) => {
        this.websites.push({
          id: website.name.toLowerCase(),
          name: '..' + website.name.toUpperCase(),
        });
      });
    });
    this.service.fetchUserList().subscribe(users => {
      users.forEach((username) => {
        this.usersFilter.push({
          id: username,
          name: '..' + username,
        });
      });
    })
    this.service.messageSource.asObservable().subscribe((value: string) => {
      if (value === 'refresh') {
        // trigger documentService to update the list
        this.fetchDocuments();
      }
    });

    this.searchTermChanged
      .pipe(debounceTime(600), distinctUntilChanged())
      .subscribe((model) => {
        this.documentService.searchTerm = model;
        this.offset = 0;
        this.fetchDocuments();
      });
  }

  fetchDocumentsLazy(event: LazyLoadEvent) {
    if (event.sortField) {
      let sortOrder = event.sortOrder == 1 ? '' : '-';
      this.documentService.sortBy = sortOrder + event.sortField;
    }
    this.documentService.offset = event.first;
    this.documentService.rows = event.rows;
    this.fetchDocuments();
  }

  fetchStateValues() {
    this.stateValues.push({ label: 'With selected..', value: 'none' });
    this.service.getConceptStateValues().subscribe((states) => {
      states.forEach((state) => {
        this.stateValues.push({ label: state, value: state });
      });
    });
  }

  fetchDocuments() {
    this.checkFilters();
    // Fetch documents list
    this.documentService.search().subscribe((results) => {
      this.documents = results.results;

      this.collectionSize = results.count;
      // Fetch statistics
      this.service.getDocumentStats().subscribe((result) => {
        this.stats.totalDocuments = result.count_total;
        // Human
        this.stats.unvalidatedSize = result.count_unvalidated;
        this.stats.acceptedSize = result.count_accepted;
        this.stats.rejectedSize = result.count_rejected;
        this.stats.classifiedSize =
          this.stats.acceptedSize + this.stats.rejectedSize;

        this.stats.classifiedPercent =
          (this.stats.classifiedSize / this.stats.totalDocuments) * 100;
        this.stats.classifiedPercent =
          Math.round((this.stats.classifiedPercent + Number.EPSILON) * 100) /
          100;

        this.stats.unvalidatedPercent =
          (this.stats.unvalidatedSize /
            (this.stats.classifiedSize + this.stats.unvalidatedSize)) *
          100;
        this.stats.unvalidatedPercent =
          Math.round((this.stats.unvalidatedPercent + Number.EPSILON) * 100) /
          100;

        this.stats.acceptedPercent =
          (this.stats.acceptedSize /
            (this.stats.classifiedSize + this.stats.unvalidatedSize)) *
          100;
        this.stats.acceptedPercent =
          Math.round((this.stats.acceptedPercent + Number.EPSILON) * 100) / 100;

        this.stats.rejectedPercent =
          (this.stats.rejectedSize /
            (this.stats.classifiedSize + this.stats.unvalidatedSize)) *
          100;
        this.stats.rejectedPercent =
          Math.round((this.stats.rejectedPercent + Number.EPSILON) * 100) / 100;

        // Classifier
        this.stats.autoUnvalidatedSize = result.count_autounvalidated;
        this.stats.autoAcceptedSize = result.count_autoaccepted;
        this.stats.autoRejectedSize = result.count_autorejected;
        this.stats.autoClassifiedSize =
          this.stats.autoAcceptedSize + this.stats.autoRejectedSize;

        this.stats.autoClassifiedPercent =
          (this.stats.autoClassifiedSize / this.stats.totalDocuments) * 100;
        this.stats.autoClassifiedPercent =
          Math.round(
            (this.stats.autoClassifiedPercent + Number.EPSILON) * 100
          ) / 100;

        this.stats.autoUnvalidatedPercent =
          (this.stats.autoUnvalidatedSize /
            (this.stats.autoClassifiedSize + this.stats.autoUnvalidatedSize)) *
          100;
        this.stats.autoUnvalidatedPercent =
          Math.round(
            (this.stats.autoUnvalidatedPercent + Number.EPSILON) * 100
          ) / 100;

        this.stats.autoAcceptedPercent =
          (this.stats.autoAcceptedSize /
            (this.stats.autoClassifiedSize + this.stats.autoUnvalidatedSize)) *
          100;
        this.stats.autoAcceptedPercent =
          Math.round((this.stats.autoAcceptedPercent + Number.EPSILON) * 100) /
          100;

        this.stats.autoRejectedPercent =
          (this.stats.autoRejectedSize /
            (this.stats.autoClassifiedSize + this.stats.autoUnvalidatedSize)) *
          100;
        this.stats.autoRejectedPercent =
          Math.round((this.stats.autoRejectedPercent + Number.EPSILON) * 100) /
          100;

        // Fill dropdowns
        if (this.ranInit == false) {
          this.fetchCelexOptions();
          this.fetchTypeOptions();
          this.fetchStatusOptions();
          this.fetchEliOptions();
          this.fetchAuthorOptions();
          this.fetchEffectDateOptions();
          this.fetchStateValues();
          this.ranInit = true;
        }
      });
    });
  }

  onAddTag(event, tags, documentId) {
    const newTag = new Tag('', event.value, documentId);
    this.service.addTag(newTag).subscribe((addedTag) => {
      // primeng automatically adds the string value first, delete this as workaround
      // see: https://github.com/primefaces/primeng/issues/3419
      tags.splice(-1, 1);
      // now add the tag object
      tags.push(addedTag);
    });
  }

  onRemoveTag(event) {
    this.confirmationService.confirm({
      message: 'Are you sure that you want to perform this action?',
      accept: () => {
        this.service.deleteTag(event.value.id).subscribe();
      },
      reject: () => {
        this.fetchDocuments();
      }
    });
  }

  onClickTag(event) {
    this.documentService.filterTag = event.value.value;
    this.filterResetPage();
    this.checkFilters();
  }

  onSearch(keyword: string) {
    this.documentService.offset = 0;
    this.searchTermChanged.next(keyword);
  }

  filterResetPage() {
    this.documentService.offset = 0;
    this.first = 0;
    this.fetchDocuments();
  }

  setIndex(index: string) {
    this.selectedIndex = index;
  }

  checkFilters() {
    this.filterActive =
      this.documentService.searchTerm.length > 0 ||
      this.documentService.filterTag.length > 0 ||
      this.documentService.showOnlyOwn != false ||
      this.documentService.filterType != '' ||
      this.documentService.website != '' ||
      this.documentService.otherUser != '' ||
      this.documentService.celex != '' ||
      this.documentService.type != '' ||
      this.documentService.status != '' ||
      this.documentService.eli != '' ||
      this.documentService.author != '' ||
      this.documentService.date_of_effect != '' ||
      this.documentService.bookmarks != false;
  }

  resetFilters() {
    this.documentService.searchTerm = '';
    this.documentService.filterTag = '';
    this.documentService.showOnlyOwn = false;
    this.documentService.filterType = '';
    this.documentService.website = '';
    this.documentService.celex = '';
    this.documentService.type = '';
    this.documentService.status = '';
    this.documentService.eli = '';
    this.documentService.author = '';
    this.documentService.otherUser = '';
    this.documentService.date_of_effect = '';
    this.documentService.bookmarks = false;
    // Dropdowns
    this.selectedCelex = '';
    this.selectedType = '';
    this.selectedStatus = '';
    this.selectedEli = '';
    this.selectedAuthor = '';
    this.selectedEffectDate = '';
    this.fetchDocuments();
  }

  updateChart1(event: Event) {
    this.data1 = {
      labels: ['Unvalidated', 'Accepted', 'Rejected'],
      datasets: [
        {
          data: [
            this.stats.autoUnvalidatedPercent,
            this.stats.autoAcceptedPercent,
            this.stats.autoRejectedPercent,
          ],
          backgroundColor: ['#36A2EB', '#28A745', '#F47677'],
          hoverBackgroundColor: ['#36A2EB', '#28A745', '#F47677'],
        },
      ],
    };
  }

  updateChart2(event: Event) {
    this.data2 = {
      labels: ['Unvalidated', 'Accepted', 'Rejected'],
      datasets: [
        {
          data: [
            this.stats.unvalidatedPercent,
            this.stats.acceptedPercent,
            this.stats.rejectedPercent,
          ],
          backgroundColor: ['#36A2EB', '#28A745', '#F47677'],
          hoverBackgroundColor: ['#36A2EB', '#28A745', '#F47677'],
        },
      ],
    };
  }

  containsGroup(groups: Array<any>, groupName: string) {
    return groups.some((group) => group.name == groupName);
  }

  onAddBookmark(document: Document) {
    this.service
      .addBookmark(this.currentDjangoUser, document)
      .subscribe((dc) => {
        document.bookmark = true;
      });
  }

  onRemoveBookmark(document: Document) {
    this.service.removeBookmark(document).subscribe((dc) => {
      // this.document.bookmark = false;
      document.bookmark = false;
    });
  }

  fetchCelexOptions() {
    this.service.fetchCelexOptions().subscribe((res) => {
      this.celexOptions = res;
    });
  }

  fetchTypeOptions() {
    this.service.fetchTypeOptions().subscribe((res) => {
      this.typeOptions = res;
    });
  }

  fetchStatusOptions() {
    this.service.fetchStatusOptions().subscribe((res) => {
      this.statusOptions = res;
    });
  }

  fetchEliOptions() {
    this.service.fetchEliOptions().subscribe((res) => {
      this.eliOptions = res;
    });
  }

  fetchAuthorOptions() {
    this.service.fetchAuthorOptions().subscribe((res) => {
      this.authorOptions = res;
    });
  }

  fetchEffectDateOptions() {
    this.service.fetchEffectDateOptions().subscribe((res) => {
      this.effectDateOptions = res;
    });
  }

  onQuery(type, keyword) {
    let hasMatched = true;
    switch (type) {
      case 'celex':
        this.documentService.celex = keyword.code;
        break;
      case 'type':
        this.documentService.type = keyword.code;
        break;
      case 'status':
        this.documentService.status = keyword.code;
        break;
      case 'eli':
        this.documentService.eli = keyword.code;
        break;
      case 'author':
        this.documentService.author = keyword.code;
        break;
      case 'date_of_effect':
        this.documentService.date_of_effect = keyword.code;
        break;
      default:
        hasMatched = false;
    }
    // Because typescript has no 'finally' statement..
    if (hasMatched) {
      this.filterResetPage();
    }
  }

  doAction(action: string) {
    if (action === 'Mark as bookmarked') {
      from(this.selectedDocuments).subscribe(
        (document) => {
          this.onAddBookmark(document);
        },
        (err) => console.log('error'),
        () => this.resetAction()
      );
    } else if (action === 'Remove bookmark') {
      from(this.selectedDocuments).subscribe(
        (document) => {
          this.onRemoveBookmark(document);
        },
        (err) => console.log('error'),
        () => this.resetAction()
      );
    } else {
      from(this.selectedDocuments).subscribe(
        (document) => {
          let acceptanceState = new AcceptanceState(
            null,
            document.id,
            null,
            this.action
          );
          this.service.updateState(acceptanceState).subscribe();
        },
        (err) => console.log('error'),
        () => this.resetAction()
      );
    }
  }

  resetAction() {
    this.selectedDocuments = [];
    this.action = 'none';
    // Wait a little so everything is updated in the backend
    setTimeout(() => {
      this.fetchDocuments();
    }, 500);
  }
}
