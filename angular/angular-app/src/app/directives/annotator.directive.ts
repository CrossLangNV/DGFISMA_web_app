import { Directive, ElementRef, HostListener } from '@angular/core';
import { Environment } from '../../environments/environment-variables';
import { AuthenticationService } from '../core/auth/authentication.service';

declare const annotator: any;

@Directive({
  selector: '[appAnnotator]'
})
export class AnnotatorDirective {
  private callerElement:ElementRef;
  private subjectId: string;
  private documentId: string;
  private annotationType: string;
  private app;

  private readonly ANNOTATION_STORE_ADDRESS_GLOSSARY = Environment.ANGULAR_DJANGO_API_GLOSSARY_ANNOTATIONS_URL;
  private readonly ANNOTATION_STORE_ADDRESS_RO = Environment.ANGULAR_DJANGO_API_RO_ANNOTATIONS_URL;
  private readonly subjectIdAttributeName = 'subject-id';
  private readonly documentIdAttributeName = 'doc-id';
  private readonly annotationTypeAttributeName = 'annotation-type';

  constructor(el: ElementRef, private authenticationService: AuthenticationService) {
    this.callerElement = el;
  }

  ngOnInit() {
    var self = this;
    this.subjectId = this.callerElement.nativeElement.getAttribute(this.subjectIdAttributeName);
    this.documentId = this.callerElement.nativeElement.getAttribute(this.documentIdAttributeName);
    this.annotationType = this.callerElement.nativeElement.getAttribute(this.annotationTypeAttributeName);

    var annotationStoreAddress = this.ANNOTATION_STORE_ADDRESS_GLOSSARY;
    if (this.annotationType == "ro") {
      annotationStoreAddress = this.ANNOTATION_STORE_ADDRESS_RO;
    }

    self.app = new annotator.App();
    self.app.include(annotator.ui.main, {
      element: this.callerElement.nativeElement
    });

    var authValue = '';
    let currentDjangoUser = this.authenticationService.currentDjangoUserValue;
    if (currentDjangoUser && currentDjangoUser.access_token) {
      authValue =  `Bearer ${currentDjangoUser.access_token}`;
    }

    self.app.include(annotator.storage.http, {
      prefix: annotationStoreAddress + "/" + this.annotationType + "/" + this.subjectId + "/" + this.documentId,
      headers: {Authorization: authValue}
    });
    // self.app.include(annotator.storage.debug);
    self.app.start().then(function () {
      self.app.annotations.load();
    });
  }

}

