import {
  Component,
  OnInit,
  Directive,
  Input,
  Output,
  EventEmitter,
  ViewChildren,
  QueryList
} from '@angular/core';
import { ApiService } from 'src/app/core/services/api.service';
import { ReportingObligation } from 'src/app/shared/models/ro';
import { IconDefinition } from '@fortawesome/fontawesome-svg-core';
import {
  faUserAlt,
  faUserLock,
  faMicrochip,
  faSyncAlt,
  faStopCircle,
  faSort,
  faSortUp,
  faSortDown,
} from '@fortawesome/free-solid-svg-icons';
import { from, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { Router } from '@angular/router';
import { AuthenticationService } from '../../core/auth/authentication.service';
import { DjangoUser } from '../../shared/models/django_user';
import { RdfFilter } from '../../shared/models/rdfFilter';
import { RoTag } from '../../shared/models/RoTag';
import { LazyLoadEvent } from 'primeng/api/lazyloadevent';
import { SelectItem } from 'primeng/api/selectitem';
import { RoAcceptanceState } from '../../shared/models/roAcceptanceState';
import { DocumentService } from 'src/app/core/services/document.service';
import { ConfirmationService } from 'primeng/api';
import { DbQuery } from '../../shared/models/dbquery';
import { Concept } from '../../shared/models/concept';
import * as FileSaver from 'file-saver';

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

export interface RoDetail {
  name: string;
}

@Directive({
  selector: 'th[sortable]',
  host: {
    '[class.asc]': 'direction === "asc"',
    '[class.desc]': 'direction === "desc"',
    '(click)': 'rotate()',
  },
})
export class NgbdSortableHeaderDirective {
  @Input() sortable: string;
  @Input() direction: SortDirection = '';
  @Output() sort = new EventEmitter<SortEvent>();

  rotate() {
    this.direction = rotate[this.direction];
    this.sort.emit({ column: this.sortable, direction: this.direction });
  }
}

@Component({
  selector: 'app-ro-list',
  templateUrl: './ro-list.component.html',
  styleUrls: ['./ro-list.component.css'],
})
export class RoListComponent implements OnInit {
  @ViewChildren(NgbdSortableHeaderDirective) headers: QueryList<
    NgbdSortableHeaderDirective
  >;
  ros: ReportingObligation[];
  selectedRos: ReportingObligation[] = [];

  availableItems: RdfFilter[]
  availableItemsQuery: Map<string, string>;

  selectedTags: Map<string, Array<string>>;

  selected: string;
  collectionSize = 0;
  selectedIndex: string = null;
  keyword = '';
  filterTag = '';
  sortBy = 'name';
  filterType = '';
  searchTermChanged: Subject<string> = new Subject<string>();
  userIcon: IconDefinition = faUserAlt;
  userLockIcon: IconDefinition = faUserLock;
  chipIcon: IconDefinition = faMicrochip;
  reloadIcon: IconDefinition = faSyncAlt;
  resetIcon: IconDefinition = faStopCircle;
  nameSortIcon: IconDefinition = faSort;
  dateSortIcon: IconDefinition = faSortDown;
  statesSortIcon: IconDefinition = faSort;
  currentDjangoUser: DjangoUser;

  websites = [{ id: '', name: 'Website..' }];
  website = ''

  filters = [
    { id: '', name: 'Acceptance state..' },
    { id: 'unvalidated', name: '..Unvalidated' },
    { id: 'accepted', name: '..Accepted' },
    { id: 'rejected', name: '..Rejected' },
  ];

  usersFilter = [
    { id: '', name: 'Validated by..' },
    { id: 'auto-classifier', name: '..Auto-classifier' },
  ];
  otherUser = '';

  fromBookmarked: boolean = false;

  contentLoaded = false;

  collapsed = true;
  offset = 0;
  rows = 5;
  action = 'none';
  stateValues: SelectItem[] = [];
  roFilterResults: string[];

  showDbQueries = false;
  dbQueries: DbQuery[];
  latestQuery: DbQuery;
  selectedConcepts: Concept[] = [];

  constructor(
    private service: ApiService,
    private router: Router,
    private authenticationService: AuthenticationService,
    private documentService: DocumentService,
    private confirmationService: ConfirmationService
  ) { }

  ngOnInit() {
    this.availableItemsQuery = new Map<string, string>();
    this.selectedTags = new Map<string, Array<string>>();

    this.authenticationService.currentDjangoUser.subscribe((x) => {
      this.currentDjangoUser = x;
      this.documentService.username = x.username;
    });

    // Force login page when not authenticated
    if (this.currentDjangoUser == null) {
      this.router.navigate(['/login']);
    }

    this.fetchUserList();
    this.fetchWebsites();

    // Fetch RDF for filters
    this.fetchAvailableFilters();
    this.fetchStateValues();

    this.fetchDbQueries();

    this.service.messageSource.asObservable().subscribe((value: string) => {
      if (value === 'refresh') {
        this.fetchRos();
      }
    });

    this.fetchRos();
    this.searchTermChanged
      .pipe(debounceTime(600), distinctUntilChanged())
      .subscribe((model) => {
        this.keyword = model;
        this.offset = 0;
        this.fetchRos();
      });
  }

  fetchWebsites() {
    this.service.getWebsites().subscribe((websites) => {
      websites.forEach((website) => {
        this.websites.push({
          id: website.name.toLowerCase(),
          name: '..' + website.name.toUpperCase(),
        });
      });
    });
  }

  fetchUserList() {
    this.service.fetchUserList().subscribe(users => {
      users.forEach((username) => {
        this.usersFilter.push({
          id: username,
          name: '..' + username,
        });
      });
    });
  }

  fetchAvailableFilters() {
    this.service
      .fetchDropdowns()
      .subscribe((results) => {
        this.availableItems = results
        this.contentLoaded = true;
      })
  }

  fetchDbQueries() {
    this.service
      .getDbQueries(
        0,
        0,
        this.currentDjangoUser.username,
        'obligations'
      )
      .subscribe((results) => {
        this.dbQueries = results.results;
        this.latestQuery = results.results[0]
      })
  }

  fetchRos() {
    this.service
      .getRdfRos(
        this.offset,
        this.rows,
        this.keyword,
        this.filterTag,
        this.filterType,
        this.sortBy,
        this.selectedTags,
        this.website,
        this.otherUser,
        this.fromBookmarked,
        this.showDbQueries,
      )
      .subscribe((results) => {
        this.ros = results.results;
        this.collectionSize = results.count;
      });
  }

  filterResetPage() {
    this.offset = 0;
    this.fetchRos();
  }

  resetFilters() {
    this.availableItems = [];
    this.availableItemsQuery.clear();
    this.selectedTags.clear();
    this.fetchAvailableFilters();
    this.fromBookmarked = false;
    this.fetchRos();
  }

  setIndex(index: string) {
    this.selectedIndex = index;
  }

  fetchStateValues() {
    this.stateValues.push({ label: 'With selected..', value: 'none' });
    this.service.getRoStateValues().subscribe((states) => {
      states.forEach((state) => {
        this.stateValues.push({ label: state, value: state });
      });
    });
  }

  onSort({ column, direction }: SortEvent) {
    console.log('sort(' + column + '/' + direction + ')');
    // resetting other headers
    this.headers.forEach((header) => {
      if (header.sortable !== column) {
        header.direction = '';
      }
    });

    // sorting documents, default date descending (-date)
    if (direction === '') {
      this.sortBy = 'name';
      this.nameSortIcon = faSort;
      this.dateSortIcon = faSortDown;
      this.statesSortIcon = faSort;
      this.fetchRos();
    } else {
      this.sortBy = direction === 'asc' ? '' : '-';
      if (column === 'states') {
        column = 'acceptance_state_max_probability';
      }
      this.sortBy += column;
      const sortIcon = direction === 'asc' ? faSortUp : faSortDown;
      if (column === 'name') {
        this.nameSortIcon = sortIcon;
        this.dateSortIcon = faSort;
        this.statesSortIcon = faSort;
      } else if (column === 'date') {
        this.dateSortIcon = sortIcon;
        this.nameSortIcon = faSort;
        this.statesSortIcon = faSort;
      } else {
        this.statesSortIcon = sortIcon;
        this.nameSortIcon = faSort;
        this.dateSortIcon = faSort;
      }
      this.fetchRos();
    }
  }

  onAddTag(event, tags, roId) {
    const newTag = new RoTag('', event.value, roId);
    this.service.addRoTag(newTag).subscribe((addedTag) => {
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
        this.service.deleteRoTag(event.value.id).subscribe();
      },
      reject: () => {
        this.fetchRos();
      }
    });

  }

  onClickTag(event) {
    this.filterTag = event.value.value;
    this.fetchRos();
  }

  numSequence(n: number): Array<number> {
    return Array(n);
  }

  containsGroup(groups: Array<any>, groupName: string) {
    return groups.some(group => group.name === groupName);
  }

  fetchRosLazy(event: LazyLoadEvent) {
    const sortOrder = event.sortOrder === 1 ? '' : '-';
    this.sortBy = sortOrder + event.sortField;
    this.offset = event.first;
    this.rows = event.rows;
    this.fetchRos();
  }

  doAction() {
    from(this.selectedRos).subscribe(
      (ro) => {
        const acceptanceState = new RoAcceptanceState(
          null,
          ro.id,
          null,
          this.action
        );
        this.service.updateRoState(acceptanceState).subscribe();
      },
      (err) => console.log('error'),
      () => {
        this.selectedRos = [];
        this.action = 'none';
        // Wait a little so everything is updated in the backend
        setTimeout(() => {
          this.fetchRos();
        }, 500);
      }
    );
  }

  search(filter: RdfFilter, event) {
    this.service.fetchReportingObligationFiltersLazy(filter, event.query, this.selectedTags, this.website, this.fromBookmarked).subscribe(data => {
      this.roFilterResults = data;

      if (event.query === '') {
        this.availableItemsQuery.delete(filter.toString())
      } else {
        this.availableItemsQuery.set(filter.toString(), event.value)
      }
      this.filterResetPage();
    })
  }

  onChangeFilter(filter: RdfFilter, event, action) {
    const filterKey = filter.toString()
    const previousValues = this.selectedTags.get(filterKey)
    const values = []

    if (action === 'add') {
      if (previousValues) {
        previousValues.forEach(key => {
          values.push(key)
        })
      }

      if (!(values.includes(event.name))) {
        values.push(event.name)
      }

      this.selectedTags.set(filterKey, values)
    } else {
      previousValues.pop()
      // Check if it happens to be completely empty now
      if (previousValues.length === 0) {
        // this.selectedTags.set(filterKey, null)
        this.selectedTags.delete(filterKey)
      } else {
        this.selectedTags.set(filterKey, previousValues)
      }
    }

    this.fetchRos()
  }

  getPlaceholder(filter: RdfFilter) {
    return this.service.rdf_get_name_of_entity(filter)
  }

  showOnlyFromBookmarkedCheck(event) {
    if (event.checked) {
      this.fromBookmarked = true;
      this.fetchRos();
    }
    else {
      this.fromBookmarked = false;
      this.fetchRos();
    }
  }

  exportCSV() {
    this.service
      .getRdfRosAsCsv(
        this.offset,
        this.rows,
        this.keyword,
        this.filterTag,
        this.filterType,
        this.sortBy,
        this.selectedTags,
        this.website,
        this.otherUser,
        this.showDbQueries,
      )
      .subscribe((data) => {
        console.log(data)

        const CSV_TYPE = 'text/csv;charset=UTF-8';
        const csvData: Blob = new Blob([data], {
          type: CSV_TYPE
        });
        const CSV_EXTENSION = '.csv'
        FileSaver.saveAs(csvData, 'RO_export.csv');
      });
  }
}

