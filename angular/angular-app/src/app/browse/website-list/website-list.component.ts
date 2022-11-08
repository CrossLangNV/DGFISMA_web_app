import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Website } from '../../shared/models/website';
import { IconDefinition } from '@fortawesome/fontawesome-svg-core';
import { faPlus } from '@fortawesome/free-solid-svg-icons';

@Component({
  selector: 'app-website-list',
  templateUrl: './website-list.component.html',
  styleUrls: ['./website-list.component.css']
})
export class WebsiteListComponent implements OnInit {
  websites = [];
  addIcon: IconDefinition;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.apiService.getWebsites().subscribe(websites => {
      this.websites = websites as Website[];
    });
    this.addIcon = faPlus;
  }

  onDelete(id) {
    this.apiService.deleteWebsite(id).subscribe();
  }
}
