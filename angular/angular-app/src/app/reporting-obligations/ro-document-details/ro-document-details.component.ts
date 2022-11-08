import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { ActivatedRoute, Router, ParamMap } from '@angular/router';
import { ApiService } from 'src/app/core/services/api.service';
import { switchMap } from 'rxjs/operators';
import { Document } from 'src/app/shared/models/document';
import { ReportingObligation } from 'src/app/shared/models/ro';
import { DirectivesModule } from '../../directives/directives.module';
import { AnnotatorDirective } from '../../directives/annotator.directive';

@Component({
  selector: 'app-ro-document-details',
  templateUrl: './ro-document-details.component.html',
  styleUrls: ['./ro-document-details.component.css'],
})
export class RoDocumentDetailsComponent implements OnInit {
  document: Document;
  ro: ReportingObligation;
  //consolidatedVersions = new Map();
  //content_html: string;
  content_html_ro: string;

  instanceType: string = "ro_highlight";
  instanceTypeAnnotations: string = "ro";
  term: string = "unknown";
  consolidatedVersions = new Map();
  content_html: string;
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private service: ApiService
  ) {
    this.route.paramMap
      .pipe(
        switchMap((params: ParamMap) =>
          this.service.getReportingObligationsView(params.get('documentId'))
        )
      ).subscribe((response) => {
        this.content_html_ro = 'No reporting obligations available'

        if (response !== null) {
          this.content_html_ro = response
        }
      });
  }

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        switchMap((params: ParamMap) =>
          this.service.getRo(params.get('roId'))
        )
      )
      .subscribe((ro) => {
        this.ro = ro;
        this.route.paramMap
          .pipe(
            switchMap((params: ParamMap) =>
              this.service.getDocument(params.get('documentId'))
            )
          )
          .subscribe((document) => {
            this.document = document;
            this.service
              .getDocumentWithContent(document.id)
              .subscribe((doc) => {

                this.service
                  .searchSolrPreAnalyzedDocument(
                    this.document.id,
                    1,
                    1,
                    this.ro.definition,
                    this.instanceType,
                    [],
                    'id',
                    'asc'
                  )
                  .subscribe((data) => {

                    if (data[1].highlighting[this.document.id]) {
                      if (data[1].highlighting[this.document.id][this.instanceType].length > 0) {
                        console.log('Showing original SOLR highlighting.')
                        this.content_html = data[1].highlighting[this.document.id][this.instanceType];
                      }
                    } else {
                      this.content_html = String(this.highlight(doc.content, ro));
                      console.log('Fallback')
                    }


                  });
              });
          });
      });
  }

  highlight(xhtml, concept): string {
    const searchMask = this.escapeRegex(concept.name);
    var regEx = new RegExp(searchMask, 'ig');
    var replaceMask = '<span class="highlight">' + concept.name + '</span>';
    return xhtml.replace(regEx, replaceMask);
  }

  escapeRegex(string: string) {
    return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
  }

  goToLink(url: string) {
    window.open(url, '_blank');
  }

  showOriginalHighlightingCheck(event) {
    var stylesheet = <CSSStyleSheet>document.styleSheets[0];
    if (event.checked) {
      stylesheet.deleteRule(0);
    }
    else {
      stylesheet.insertRule(".highlight { background-color: transparent !important;}", 0);
    }
  }
}
