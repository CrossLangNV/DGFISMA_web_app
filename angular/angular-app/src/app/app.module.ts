import { AppComponent } from './app.component';
import { CoreModule } from './core/core.module';
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { SharedModule } from './shared/shared.module';
import { BrowseModule } from './browse/browse.module';
import { AppRoutingModule } from './app-routing.module';
import { GlossaryModule } from './glossary/glossary.module';
import { ReportingObligationsModule } from './reporting-obligations/reporting-obligations.module';
import { NgxSkeletonLoaderModule} from "ngx-skeleton-loader";

@NgModule({
  declarations: [AppComponent],
  imports: [
    AppRoutingModule,
    SharedModule,
    BrowserModule,
    BrowserAnimationsModule,
    CoreModule,
    GlossaryModule,
    ReportingObligationsModule,
    BrowseModule,
    NgxSkeletonLoaderModule,
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
