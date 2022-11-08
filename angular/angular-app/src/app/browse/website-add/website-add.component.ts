import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Router } from '@angular/router';

import { Website } from '../../shared/models/website';

@Component({
  selector: 'app-website-add',
  templateUrl: './website-add.component.html',
  styleUrls: ['./website-add.component.css']
})
export class WebsiteAddComponent {
  model = new Website('', '', '', '', 0);

  submitted = false;

  constructor(private apiService: ApiService, private router: Router) {}

  onSubmit() {
    this.submitted = true;
    this.apiService
      .createWebsite(this.model)
      .subscribe(website => this.router.navigate(['/website']));
  }
}
