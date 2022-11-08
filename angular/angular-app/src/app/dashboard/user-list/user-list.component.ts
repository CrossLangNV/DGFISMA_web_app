import { Component, OnInit } from '@angular/core';
import { ApiAdminService } from 'src/app/core/services/api.admin.service';
import { User } from 'src/app/shared/models/user';

@Component({
  selector: 'app-user-list',
  templateUrl: './user-list.component.html',
  styleUrls: ['./user-list.component.css']
})
export class UserListComponent implements OnInit {
  users: User[] = [];

  constructor(private apiAdminService: ApiAdminService) { }

  ngOnInit() {
    this.apiAdminService.getUsers().subscribe(users => {
      this.users = users;
    })
  }

}
