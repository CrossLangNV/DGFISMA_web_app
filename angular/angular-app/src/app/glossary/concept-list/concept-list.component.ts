import { Component, OnInit } from '@angular/core';
import { ApiService } from 'src/app/core/services/api.service';
import { Concept, Lemma } from 'src/app/shared/models/concept';
import { IconDefinition } from '@fortawesome/fontawesome-svg-core';
import {
  faUserAlt,
  faUserLock,
  faMicrochip,
  faSyncAlt,
  faStopCircle,
} from '@fortawesome/free-solid-svg-icons';
import { from, Subject } from 'rxjs';
import { ConceptTag } from 'src/app/shared/models/ConceptTag';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { Router } from '@angular/router';
import { DjangoUser } from '../../shared/models/django_user';
import { AuthenticationService } from '../../core/auth/authentication.service';
import { LazyLoadEvent } from 'primeng/api/lazyloadevent';
import { SelectItem } from 'primeng/api/selectitem';
import { ConceptAcceptanceState } from '../../shared/models/conceptAcceptanceState';
import {ConfirmationService} from 'primeng/api';
import {DbQuery} from '../../shared/models/dbquery';
import { saveAs } from 'file-saver';
import * as FileSaver from 'file-saver';

@Component({
  selector: 'app-concept-list',
  templateUrl: './concept-list.component.html',
  styleUrls: ['./concept-list.component.css'],
})
export class ConceptListComponent implements OnInit {
  concepts: Concept[];
  lemmas: Lemma[];
  dbQueries: DbQuery[];
  latestQuery: DbQuery;
  selectedConcepts: Concept[] = [];
  collectionSize = 0;
  selectedIndex: string = null;
  modes: SelectItem[] = [];
  currentMode = 'concepts';
  offset = 0;
  rows = 5;
  keyword = '';
  filterTag = '';
  sortBy = 'name';
  filterType = '';
  version = '8a4f1d58';
  showBookmarked = false;
  showOnlyOwn = false;
  showDbQueries = false;
  website = '';
  filterActive = false;
  action = 'none';
  actionDisabled = true;
  stateValues: SelectItem[] = [];
  searchTermChanged: Subject<string> = new Subject<string>();
  userIcon: IconDefinition = faUserAlt;
  userLockIcon: IconDefinition = faUserLock;
  chipIcon: IconDefinition = faMicrochip;
  reloadIcon: IconDefinition = faSyncAlt;
  resetIcon: IconDefinition = faStopCircle;
  currentDjangoUser: DjangoUser;
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
  otherUser = '';

  constructor(
    private service: ApiService,
    private router: Router,
    private authenticationService: AuthenticationService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit() {
    this.authenticationService.currentDjangoUser.subscribe(
      (x) => (this.currentDjangoUser = x)
    );

    // Force login page when not authenticated
    if (this.currentDjangoUser == null) {
      this.router.navigate(['/login']);
    }

    this.fetchWebsites();
    this.fetchStateValues();
    this.fetchUserList();

    this.fetchDbQueries();

    this.service.messageSource.asObservable().subscribe((value: string) => {
      if (value === 'refresh') {
        this.fetchObjects();
      }
    });

    this.searchTermChanged
      .pipe(debounceTime(600), distinctUntilChanged())
      .subscribe((model) => {
        this.keyword = model;
        this.offset = 0;
        this.fetchObjects();
      });

    this.modes.push({ label: 'Concepts', value: 'concepts' });
    this.modes.push({ label: 'Lemmas', value: 'lemmas' });
  }

  fetchUserList() {
    this.service.fetchUserList().subscribe(users => {
      users.forEach((username) => {
        this.usersFilter.push({
          id: username,
          name: '..' + username,
        });
      });
    })
  }

  fetchStateValues() {
    this.stateValues.push({ label: 'With selected..', value: 'none' });
    this.service.getConceptStateValues().subscribe((states) => {
      states.forEach((state) => {
        this.stateValues.push({ label: state, value: state });
      });
    });
  }

  fetchObjectsLazy(event: LazyLoadEvent) {
    const sortOrder = event.sortOrder == 1 ? '' : '-';
    this.sortBy = sortOrder + event.sortField;
    this.offset = event.first;
    this.rows = event.rows;
    this.fetchObjects();
  }

  fetchObjects() {
    if (this.currentMode == 'concepts') {
      this.fetchConcepts();
    }
    if (this.currentMode == 'lemmas') {
      this.fetchLemmas();
    }
  }

  fetchLemmas() {
    this.checkFilters();
    this.service
      .getLemmas(
        this.offset,
        this.rows,
        this.keyword,
        this.filterTag,
        this.filterType,
        this.version,
        this.showBookmarked,
        this.showOnlyOwn,
        this.website,
        this.sortBy,
        this.otherUser,
        this.showDbQueries,
      )
      .subscribe((results) => {
        this.lemmas = results.results;
        this.collectionSize = results.count;
      });
  }

  fetchConcepts() {
    this.checkFilters();
    this.service
      .getConcepts(
        this.offset,
        this.rows,
        this.keyword,
        this.filterTag,
        this.filterType,
        this.version,
        this.showBookmarked,
        this.showOnlyOwn,
        this.website,
        this.sortBy,
        this.otherUser,
        this.showDbQueries,
      )
      .subscribe((results) => {
        this.concepts = results.results;
        this.collectionSize = results.count;
      });
  }



  fetchDbQueries() {
    this.service
      .getDbQueries(
        0,
        0,
        this.currentDjangoUser.username,
        'glossary'
      )
      .subscribe((results) => {
        this.dbQueries = results.results;
        this.latestQuery = results.results[0]
      })
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

  onSearch(keyword: string) {
    this.searchTermChanged.next(keyword);
  }

  changePage(pageNumber) {
    this.offset = this.rows * pageNumber;
    this.fetchObjects();
  }

  filterResetPage() {
    this.offset = 0;
    this.fetchObjects();
    this.router.navigate(['/glossary']);
  }

  resetFilters() {
    this.keyword = '';
    this.filterTag = '';
    this.filterType = '';
    this.website = '';
    this.otherUser = '';
    this.showBookmarked = false;
    this.showOnlyOwn = false;
    this.filterResetPage();
  }

  checkFilters() {
    this.filterActive =
      this.keyword.length > 0 ||
      this.filterTag.length > 0 ||
      this.showBookmarked ||
      this.showOnlyOwn ||
      this.filterType !== '' ||
      this.otherUser != '' ||
      this.website !== '';
  }

  setIndex(index: string) {
    this.selectedIndex = index;
  }

  onAddTag(event, tags, conceptId) {
    const newTag = new ConceptTag('', event.value, conceptId);
    this.service.addConceptTag(newTag).subscribe((addedTag) => {
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
        this.service.deleteConceptTag(event.value.id).subscribe();
      },
      reject: () => {
        this.fetchConcepts();
      }
    });

  }

  onClickTag(event) {
    this.filterTag = event.value.value;
    this.fetchObjects();
  }

  containsGroup(groups: Array<any>, groupName: String) {
    if (groups != null) {
      return groups.some((group) => group.name == groupName);
    }
  }

  doAction() {
    from(this.selectedConcepts).subscribe(
      (concept) => {
        const acceptanceState = new ConceptAcceptanceState(
          null,
          concept.id,
          null,
          this.action
        );
        this.service.updateConceptState(acceptanceState).subscribe();
      },
      (err) => console.log('error'),
      () => {
        this.selectedConcepts = [];
        this.action = 'none';
        // Wait a little so everything is updated in the backend
        setTimeout(() => {
          this.fetchObjects();
        }, 500);
      }
    );
  }

  onModeChange(event) {
    this.fetchObjects();
  }


  exportCSV() {
    this.service
      .getConceptsAsCsv(
        this.offset,
        this.rows,
        this.keyword,
        this.filterTag,
        this.filterType,
        this.version,
        this.showBookmarked,
        this.showOnlyOwn,
        this.website,
        this.sortBy,
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
        FileSaver.saveAs(csvData, 'concept_export.csv');
      });
  }
}
