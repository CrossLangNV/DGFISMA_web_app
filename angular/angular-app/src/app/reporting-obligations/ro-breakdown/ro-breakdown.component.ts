import {Component, OnInit, ViewEncapsulation} from '@angular/core';
import { ActivatedRoute, Router, ParamMap } from '@angular/router';
import { ApiService } from 'src/app/core/services/api.service';
import { switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-ro-breakdown',
  templateUrl: './ro-breakdown.component.html',
  styleUrls: ['./ro-breakdown.component.css'],
  encapsulation: ViewEncapsulation.ShadowDom,

})
export class RoBreakdownComponent implements OnInit {
  content_html_ro: string;

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
        this.content_html_ro = response
    });
  }

  ngOnInit(): void {
  }
}
