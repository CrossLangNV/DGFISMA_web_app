import { NgModule } from '@angular/core';
import { LoginComponent } from './login-component/login.component';
import { AlertComponent } from './alert-component/alert.component';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { BreadcrumbComponent } from './breadcrumb-component/breadcrumb.component';
import { BreadcrumbModule } from 'primeng/breadcrumb';

@NgModule({
  declarations: [
    LoginComponent,
    AlertComponent,
    BreadcrumbComponent
  ],
  imports: [
    CommonModule,
    RouterModule,
    NgbModule,
    ReactiveFormsModule,
    FormsModule,
    FontAwesomeModule,
    BreadcrumbModule
  ],
  exports: [
    CommonModule,
    RouterModule,
    LoginComponent,
    AlertComponent,
    FormsModule,
    ReactiveFormsModule,
    NgbModule,
    FontAwesomeModule,
    BreadcrumbModule,
    BreadcrumbComponent
  ]
})
export class SharedModule {}
